provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "x_bucket" {
  bucket        = var.bucket_name
  force_destroy = true
}

resource "aws_s3_object" "raw_folder" {
  bucket = aws_s3_bucket.x_bucket.id
  key    = "raw/"
  source = "empty.txt"
  etag   = filemd5("empty.txt")
}

resource "aws_s3_object" "processed_folder" {
  bucket = aws_s3_bucket.x_bucket.id
  key    = "processed/"
  source = "empty.txt"
  etag   = filemd5("empty.txt")
}

resource "aws_s3_object" "csv_upload" {
  bucket        = var.bucket_name
  key           = "raw/sales_data_dirty_20_errores.csv"
  source        = "${path.module}/sales_data_dirty_20_errores.csv"
  etag          = filemd5("${path.module}/sales_data_dirty_20_errores.csv")
  content_type  = "text/csv"
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_csv_exec_role"

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
   lifecycle {
    ignore_changes = [name]
  }
}


resource "aws_iam_policy_attachment" "lambda_policy" {
  name       = "lambda_policy_attachment"
  roles      = [aws_iam_role.lambda_exec_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_lambda_function" "csv_corrector" {
  function_name = "csv_corrector_lambda"
  filename      = "${path.module}/lambda.zip"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  role          = aws_iam_role.lambda_exec_role.arn
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  depends_on    = [aws_iam_policy_attachment.lambda_policy]
}

resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_corrector.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.x_bucket.arn
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.x_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.csv_corrector.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.s3_invoke_permission]
}
