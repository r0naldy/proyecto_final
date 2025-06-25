provider "aws" {
  region = "us-east-1"
}

# Reutilizar un rol ya existente (NO se crea)
data "aws_iam_role" "lambda_exec_role" {
  name = "lambda_csv_exec_role"
}

# Adjuntar políticas al rol existente (opcional, si no están ya)
resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = data.aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = data.aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Función Lambda con código empaquetado
resource "aws_lambda_function" "csv_corrector" {
  function_name    = "csv_corrector_lambda"
  role             = data.aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.9"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  timeout          = 3

  depends_on = [
    aws_iam_role_policy_attachment.lambda_s3,
    aws_iam_role_policy_attachment.lambda_logs
  ]
}

# Permitir que S3 invoque la función Lambda
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_corrector.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::x-bucket-cloud"
}

# Configuración de eventos S3 que disparan la Lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = "x-bucket-cloud"

  lambda_function {
    lambda_function_arn = aws_lambda_function.csv_corrector.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.s3_invoke_permission]
}

# Subir archivo CSV
resource "aws_s3_object" "csv_upload" {
  bucket       = "x-bucket-cloud"
  key          = "raw/sales_data_dirty_20_errores.csv"
  source       = "${path.module}/sales_data_dirty_20_errores.csv"
  content_type = "text/csv"
}

# Carpetas vacías para estructura del bucket
resource "aws_s3_object" "raw_folder" {
  bucket = "x-bucket-cloud"
  key    = "raw/"
  source = "${path.module}/empty.txt"
}

resource "aws_s3_object" "processed_folder" {
  bucket = "x-bucket-cloud"
  key    = "processed/"
  source = "${path.module}/empty.txt"
}
