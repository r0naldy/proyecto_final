provider "aws" {
  region = "us-east-1"
}

data "aws_iam_role" "lambda_exec_role" {
  name = "lambda_csv_exec_role"
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = data.aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = data.aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "csv_corrector" {
  function_name    = "csv_corrector_lambda"
  role             = data.aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.9"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  timeout          = 10

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash
    ]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_s3,
    aws_iam_role_policy_attachment.lambda_logs
  ]
}