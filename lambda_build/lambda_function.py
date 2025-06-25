import boto3
import pandas as pd
import io
import json

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        bucket_name = "x-bucket-cloud"
        object_key = "raw/sales_data_dirty_20_errores.csv"
        
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        csv_content = response['Body'].read().decode('utf-8')
        
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Limpieza de ejemplo (completa con las 20 reglas tuyas)
        df = df.dropna()
        df = df[df["price"] > 0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df = df[df['category'].str.len() > 1]
        df = df.drop_duplicates()
        
        json_buffer = io.StringIO()
        df.to_json(json_buffer, orient='records', lines=True)

        output_key = object_key.replace('raw/', 'processed/').replace('.csv', '.json')

        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=json_buffer.getvalue(),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'body': f'Procesado y guardado como {output_key}'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'error': str(e)
        }
        
        #123