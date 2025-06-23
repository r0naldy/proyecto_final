from flask import Flask, jsonify
import boto3
from botocore.exceptions import ClientError
import json
import os

app = Flask(__name__)

# Configuración del cliente S3
# Las credenciales se obtendrán automáticamente del rol de IAM de la instancia EC2
s3_client = boto3.client('s3')

# Obtener el nombre del bucket de una variable de entorno o usar un valor por defecto
# En un entorno real, esto se manejaría con variables de entorno o AWS Parameter Store
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'x-bucket-inicial')

@app.route('/data-json/<file_id>', methods=['GET'])
def get_cleaned_data(file_id):
    """
    Endpoint para obtener un archivo JSON limpio desde S3.
    """
    s3_key = f"processed/cleaned_{file_id}.json"
    print(f"Solicitud recibida para file_id: {file_id}, buscando en S3 key: {s3_key}")

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        json_content = response['Body'].read().decode('utf-8')
        data = json.loads(json_content)
        print(f"Archivo {s3_key} encontrado y cargado.")
        return jsonify(data), 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"Error: Archivo {s3_key} no encontrado en el bucket {S3_BUCKET_NAME}.")
            return jsonify({"error": f"Archivo con ID '{file_id}' no encontrado."}), 404
        else:
            print(f"Error inesperado de S3: {e}")
            return jsonify({"error": "Error al acceder a S3.", "details": str(e)}), 500
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON para {s3_key}: {e}")
        return jsonify({"error": "Error al procesar el archivo JSON.", "details": str(e)}), 500
    except Exception as e:
        print(f"Error interno del servidor: {e}")
        return jsonify({"error": "Error interno del servidor.", "details": str(e)}), 500

if __name__ == '__main__':
    # Gunicorn o Nginx/Gunicorn manejarán la ejecución en producción
    # Para desarrollo local, puedes ejecutarlo así:
    # app.run(debug=True, host='0.0.0.0', port=5000)
    print("La aplicación Flask está configurada. En producción, será iniciada por Gunicorn.")
