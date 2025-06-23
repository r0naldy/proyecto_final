import boto3
import os

s3 = boto3.client('s3')

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'x-bucket-inicial')

local_csv_filename = "sales_data_dirty_20_errores.csv"
s3_key = f"raw/{local_csv_filename}"

try:
    s3.upload_file(
        Filename=local_csv_filename,
        Bucket=S3_BUCKET_NAME,
        Key=s3_key
    )
    print(f"Archivo CSV '{local_csv_filename}' subido a S3 correctamente en s3://{S3_BUCKET_NAME}/{s3_key}.")
except Exception as e:
    print(f"Error al subir el archivo CSV a S3: {e}")
    print("Asegúrate de que el bucket existe y tienes los permisos correctos.")
    print("Verifica el archivo de credenciales del AWS (~/.aws/credentials) o las variables de entorno.")

