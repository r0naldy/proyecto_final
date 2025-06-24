resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Effect = "Allow",
        Sid    = ""
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "lambda_s3_access" {
  name       = "lambda-s3-attach"
  roles      = [aws_iam_role.lambda_exec_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_lambda_function" "clean_csv_lambda" {
  function_name = "clean-csv-lambda"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  timeout       = 30
  filename      = "${path.module}/../lambda_code/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda_code/lambda.zip")
}

resource "aws_lambda_permission" "s3_trigger" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.clean_csv_lambda.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.x_bucket.arn
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.x_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.clean_csv_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.s3_trigger]
}
