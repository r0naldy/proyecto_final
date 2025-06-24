resource "aws_s3_object" "csv_upload" {
  bucket        = var.bucket_name
  key           = "raw/sales_data_dirty_20_errores.csv"
  source        = "${path.module}/sales_data_dirty_20_errores.csv"
  etag          = filemd5("${path.module}/sales_data_dirty_20_errores.csv")
  content_type  = "text/csv"
}