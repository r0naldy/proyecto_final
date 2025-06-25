provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "x_bucket" {
  bucket = var.bucket_name
  force_destroy = true
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role_ronal_dev_2025_2"

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
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "json_cleaner" {
  function_name    = "json_cleaner"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  filename         = "lambda.zip"
  source_code_hash = filebase64sha256("lambda.zip")
  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }
}

resource "aws_s3_bucket_notification" "notify_lambda" {
  bucket = aws_s3_bucket.x_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.json_cleaner.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.json_cleaner.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.x_bucket.arn
}

resource "aws_instance" "consumer" {
  ami           = var.ami
  instance_type = "t2.micro"
  user_data     = file("scripts/deploy_consumer.sh")

  tags = {
    Name = "consumer-ec2"
  }
}

output "s3_bucket_name" {
  value = aws_s3_bucket.x_bucket.bucket
}

output "ec2_public_ip" {
  value = aws_instance.consumer.public_ip
}