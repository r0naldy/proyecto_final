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