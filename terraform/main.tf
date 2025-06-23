# Configuración del proveedor AWS
provider "aws" {
  region = var.aws_region
}

# --- S3 Bucket para datos RAW y procesados ---
resource "aws_s3_bucket" "x_bucket" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "x-bucket-etl"
    Environment = "dev"
  }
}

resource "aws_s3_bucket_acl" "x_bucket_acl" {
  bucket = aws_s3_bucket.x_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "x_bucket_versioning" {
  bucket = aws_s3_bucket.x_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# --- IAM Role y Policy para la función Lambda ---
resource "aws_iam_role" "lambda_etl_role" {
  name = "${var.lambda_function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.lambda_function_name}-role"
  }
}

resource "aws_iam_policy" "lambda_s3_access_policy" {
  name        = "${var.lambda_function_name}-s3-access-policy"
  description = "Permite a Lambda leer y escribir en el bucket S3"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Effect   = "Allow",
        Resource = "${aws_s3_bucket.x_bucket.arn}/*"
      },
      {
        Action = [
          "s3:ListBucket"
        ],
        Effect   = "Allow",
        Resource = aws_s3_bucket.x_bucket.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.lambda_function_name}:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_attach" {
  role       = aws_iam_role.lambda_etl_role.name
  policy_arn = aws_iam_policy.lambda_s3_access_policy.arn
}

# --- Función Lambda ---
resource "aws_lambda_function" "etl_lambda" {
  function_name = var.lambda_function_name
  runtime       = "python3.9"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_etl_role.arn
  timeout       = 300 # 5 minutos para procesamiento
  memory_size   = 512 # Suficiente para pandas y datos pequeños

  # Si el código se sube manualmente o vía CI/CD a S3
  s3_bucket = aws_s3_bucket.x_bucket.id
  s3_key    = "lambda_deploy/lambda_function.zip" # Este path será usado por CI/CD


  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
    }
  }

  tags = {
    Name = var.lambda_function_name
  }
}

# Permisos para que S3 invoque la Lambda
resource "aws_lambda_permission" "allow_s3_to_call_lambda" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.etl_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.x_bucket.arn
}

# Trigger S3 para la Lambda
resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = aws_s3_bucket.x_bucket.id

  # CAMBIO: Usar 'lambda_function' en lugar de 'lambda_queue'
  lambda_function {
    lambda_function_arn = aws_lambda_function.etl_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
  }
}

# --- IAM Role y Profile para la instancia EC2 ---
resource "aws_iam_role" "ec2_flask_role" {
  name = "ec2-flask-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
  tags = {
    Name = "ec2-flask-app-role"
  }
}

resource "aws_iam_policy" "ec2_s3_read_policy" {
  name        = "ec2-s3-read-policy"
  description = "Permite a la instancia EC2 leer del bucket S3 (solo processed/)"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:GetObject"
        ],
        Effect   = "Allow",
        Resource = "${aws_s3_bucket.x_bucket.arn}/processed/*"
      },
      {
        Action = [
          "s3:ListBucket"
        ],
        Effect   = "Allow",
        Resource = aws_s3_bucket.x_bucket.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_s3_read_attach" {
  role       = aws_iam_role.ec2_flask_role.name
  policy_arn = aws_iam_policy.ec2_s3_read_policy.arn
}

resource "aws_iam_instance_profile" "ec2_flask_profile" {
  name = "ec2-flask-app-profile"
  role = aws_iam_role.ec2_flask_role.name
}

# --- Nuevo recurso: Par de Claves EC2 ---
resource "aws_key_pair" "flask_app_key" {
  key_name   = "flask-app-key-managed-by-terraform" # Un nombre para tu key pair en AWS
  public_key = var.ssh_public_key
}

# --- Security Group para la instancia EC2 ---
resource "aws_security_group" "flask_sg" {
  name        = "flask-app-security-group"
  description = "Permite tráfico SSH y HTTP para la app Flask"
  vpc_id      = data.aws_vpc.default.id # Usar la VPC por defecto

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Limitar esto en producción a IPs conocidas
    description = "Allow SSH from anywhere"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol     = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Limitar esto en producción
    description = "Allow HTTP from anywhere"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all egress traffic"
  }

  tags = {
    Name = "flask-app-sg"
  }
}

# --- Instancia EC2 para el backend Flask ---
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "flask_app_instance" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = var.ec2_instance_type
  key_name                    = aws_key_pair.flask_app_key.key_name # CAMBIO: Referencia al nombre de la clave creada por Terraform
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.flask_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_flask_profile.name

  user_data = <<-EOF
              #!/bin/bash
              sudo yum update -y
              sudo yum install -y python3 python3-pip git nginx
              sudo pip3 install virtualenv
              sudo systemctl enable nginx
              sudo systemctl start nginx
              EOF

  tags = {
    Name = "FlaskAppInstance"
  }
}

# Datos para obtener el ID de la cuenta AWS
data "aws_caller_identity" "current" {}
data "aws_vpc" "default" {
  default = true
}

# --- Output de la infraestructura ---
output "s3_bucket_name" {
  description = "Nombre del bucket S3 creado"
  value       = aws_s3_bucket.x_bucket.id
}

output "lambda_function_name" {
  description = "Nombre de la función Lambda creada"
  value       = aws_lambda_function.etl_lambda.function_name
}

output "ec2_public_ip" {
  description = "IP Pública de la instancia EC2"
  value       = aws_instance.flask_app_instance.public_ip
}

output "ec2_public_dns" {
  description = "DNS Público de la instancia EC2"
  value       = aws_instance.flask_app_instance.public_dns
}
