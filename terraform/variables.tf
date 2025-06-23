variable "aws_region" {
  description = "La región de AWS donde se desplegarán los recursos."
  type        = string
  default     = "us-east-1" 
}

variable "s3_bucket_name" {
  description = "El nombre único del bucket S3."
  type        = string
  default     = "x-bucket-inicial" 
}

variable "lambda_function_name" {
  description = "El nombre de la función Lambda ETL."
  type        = string
  default     = "ETLDataProcessor"
}

variable "ec2_instance_type" {
  description = "El tipo de instancia EC2 para el backend Flask."
  type        = string
  default     = "t2.micro"
}

variable "ssh_public_key" {
  description = "La clave pública SSH para crear el par de claves EC2."
  type        = string
}
