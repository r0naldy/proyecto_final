resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy_attachment" "lambda_policy_attach" {
  name       = "lambda-policy-attach"
  roles      = [aws_iam_role.lambda_exec_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_rw" {
  name = "lambda-s3-rw"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::x-bucket-cloud",
          "arn:aws:s3:::x-bucket-cloud/*"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "data_cleaner_lambda" {
  function_name = "clean-csv-on-upload"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  timeout       = 30
  memory_size   = 512

  filename         = "${path.module}/../lambda_code/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda_code/lambda.zip")
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = "x-bucket-cloud"

  lambda_function {
    lambda_function_arn = aws_lambda_function.data_cleaner_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_cleaner_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::x-bucket-cloud"
}
