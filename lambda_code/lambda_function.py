import json
import csv
import io
import boto3
import re
from datetime import datetime
import pandas as pd
import numpy as np

# Inicializar cliente S3
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Función principal de la Lambda que se activa con un evento S3.
    Lee un archivo CSV del bucket 'raw/', limpia y transforma los datos,
    y guarda el resultado como JSON en el bucket 'processed/'.
    """
    print(f"Evento recibido: {json.dumps(event)}")

    # Obtener información del archivo desde el evento S3
    try:
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        file_id = file_key.split('/')[-1].replace('.csv', '')
        print(f"Procesando archivo: {file_key} del bucket: {bucket_name}")
    except KeyError as e:
        print(f"Error al parsear el evento S3: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps('Error: No se pudo obtener la información del archivo del evento S3.')
        }

    # Descargar el archivo CSV de S3
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        csv_content = response['Body'].read().decode('utf-8')
        print("Archivo CSV descargado exitosamente.")
    except Exception as e:
        print(f"Error al descargar el archivo CSV desde S3: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error al descargar el archivo desde S3: {e}')
        }

    # Leer el CSV con pandas
    try:
        df = pd.read_csv(io.StringIO(csv_content))
        print(f"DataFrame cargado con {len(df)} filas.")
    except Exception as e:
        print(f"Error al leer el archivo CSV con pandas: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error al leer el CSV: {e}')
        }

    # --- Aplicar reglas de limpieza y validación (reglas de negocio) ---
    original_rows = len(df)
    print(f"Filas originales: {original_rows}")

    # Regla 6: Eliminar registros duplicados
    df.drop_duplicates(inplace=True)
    print(f"Regla 6 (Duplicados): Filas después de eliminar duplicados: {len(df)}")

    # Regla 8: ORDERNUMBER Vacío → eliminar registro
    df.dropna(subset=['ORDERNUMBER'], inplace=True)
    print(f"Regla 8 (ORDERNUMBER vacío): Filas después de filtrar: {len(df)}")

    # Regla 9: ORDERLINENUMBER Vacío → eliminar registro
    df.dropna(subset=['ORDERLINENUMBER'], inplace=True)
    print(f"Regla 9 (ORDERLINENUMBER vacío): Filas después de filtrar: {len(df)}")

    # Regla 11: SALES Vacíos → descartar
    df.dropna(subset=['SALES'], inplace=True)
    print(f"Regla 11 (SALES vacío): Filas después de filtrar: {len(df)}")

    # Regla 1: QUANTITYORDERED Vacíos → asignar valor por defecto (0)
    df['QUANTITYORDERED'].fillna(0, inplace=True)
    # Convertir a numérico después de llenar NaNs para evitar errores
    df['QUANTITYORDERED'] = pd.to_numeric(df['QUANTITYORDERED'], errors='coerce')
    print(f"Regla 1 (QUANTITYORDERED vacíos): Procesado.")

    # Regla 10: QUANTITYORDERED Ceros → eliminar
    df = df[df['QUANTITYORDERED'] != 0]
    print(f"Regla 10 (QUANTITYORDERED ceros): Filas después de filtrar: {len(df)}")

    # Regla 2: PRICEEACH Negativos → poner como NaN
    df['PRICEEACH'] = pd.to_numeric(df['PRICEEACH'], errors='coerce')
    df.loc[df['PRICEEACH'] < 0, 'PRICEEACH'] = np.nan
    print(f"Regla 2 (PRICEEACH negativos): Procesado.")

    # Regla 16: PRICEEACH Texto no numérico → convertir si posible o eliminar (ya manejado por errors='coerce' y dropna en SALES)
    # Si después de 'coerce' quedan NaNs en PRICEEACH, los eliminamos para asegurar limpieza total
    df.dropna(subset=['PRICEEACH'], inplace=True)
    print(f"Regla 16 (PRICEEACH no numérico): Filas después de filtrar NaNs: {len(df)}")

    # Regla 3: STATUS Valores mal escritos → corregir ("DLEIVERED" → "DELIVERED")
    # Regla 15: STATUS Null → colocar "UNKNOWN"
    status_mapping = {
        'DLEIVERED': 'DELIVERED',
        'SHIPPED': 'SHIPPED',
        'IN PROCESS': 'IN PROCESS',
        'RESOLVED': 'RESOLVED',
        'CANCELLED': 'CANCELLED',
        # Agrega más mapeos si conoces otros errores comunes
    }
    df['STATUS'] = df['STATUS'].astype(str).replace(status_mapping).replace('nan', 'UNKNOWN')
    print(f"Regla 3 & 15 (STATUS): Procesado.")

    # Regla 4 & 12: ORDERDATE Fechas inválidas / Texto irreconocible → descartar
    def is_valid_date(date_str):
        if pd.isna(date_str):
            return False
        try:
            # Intentar varios formatos comunes
            for fmt in ('%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y'):
                datetime.strptime(str(date_str), fmt)
                return True
        except ValueError:
            return False
    df = df[df['ORDERDATE'].apply(is_valid_date)]
    print(f"Regla 4 & 12 (ORDERDATE inválido/irreconocible): Filas después de filtrar: {len(df)}")

    # Regla 5: SALES Texto en vez de número → convertir si posible, si no filtrar (ya cubierto por dropna anterior)
    df['SALES'] = pd.to_numeric(df['SALES'], errors='coerce')
    df.dropna(subset=['SALES'], inplace=True)
    print(f"Regla 5 (SALES texto): Filas después de filtrar: {len(df)}")

    # Regla 7: PRODUCTCODE Demasiado largo → truncar a 15 caracteres
    df['PRODUCTCODE'] = df['PRODUCTCODE'].astype(str).apply(lambda x: x[:15])
    print(f"Regla 7 (PRODUCTCODE): Procesado.")

    # Regla 13: PRODUCTLINE Demasiado largo → truncar a 30 caracteres
    df['PRODUCTLINE'] = df['PRODUCTLINE'].astype(str).apply(lambda x: x[:30])
    print(f"Regla 13 (PRODUCTLINE): Procesado.")

    # Regla 14: NUMERICCODE Texto como "abc" o "xx" → filtrar (asumiendo que debe ser numérico)
    df['NUMERICCODE'] = pd.to_numeric(df['NUMERICCODE'], errors='coerce')
    df.dropna(subset=['NUMERICCODE'], inplace=True)
    print(f"Regla 14 (NUMERICCODE texto/inválido): Filas después de filtrar: {len(df)}")

    # Regla 17: ORDERNUMBER String tipo "ORDX" → invalidar si no es número
    # Asumiendo que ORDERNUMBER debería ser un número entero.
    df['ORDERNUMBER'] = pd.to_numeric(df['ORDERNUMBER'], errors='coerce')
    df.dropna(subset=['ORDERNUMBER'], inplace=True)
    print(f"Regla 17 (ORDERNUMBER no numérico): Filas después de filtrar: {len(df)}")

    # Regla 18: ORDERLINENUMBER Texto tipo "LINEA-X" → descartar
    # Asumiendo que ORDERLINENUMBER debería ser un número entero.
    df['ORDERLINENUMBER'] = pd.to_numeric(df['ORDERLINENUMBER'], errors='coerce')
    df.dropna(subset=['ORDERLINENUMBER'], inplace=True)
    print(f"Regla 18 (ORDERLINENUMBER no numérico): Filas después de filtrar: {len(df)}")

    # Regla 19: COUNTRY Emojis → quitar o reemplazar por texto limpio
    def remove_emojis(text):
        if pd.isna(text):
            return text
        # Regex para eliminar la mayoría de los emojis y símbolos misceláneos
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', str(text)).strip()

    df['COUNTRY'] = df['COUNTRY'].apply(remove_emojis)
    print(f"Regla 19 (COUNTRY emojis): Procesado.")

    # Regla 20: CITY Vacíos → asignar "SIN CIUDAD"
    df['CITY'].fillna("SIN CIUDAD", inplace=True)
    print(f"Regla 20 (CITY vacíos): Procesado.")

    # Convertir el DataFrame limpio a formato JSON (lista de diccionarios)
    cleaned_data_json = df.to_json(orient='records', indent=4)
    processed_rows = len(df)
    print(f"Filas procesadas y limpias: {processed_rows}")
    print(f"Porcentaje de filas descartadas: {((original_rows - processed_rows) / original_rows * 100):.2f}%")

    # Subir el archivo JSON limpio a S3
    output_key = f"processed/cleaned_{file_id}.json"
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=cleaned_data_json,
            ContentType='application/json'
        )
        print(f"Archivo JSON limpio subido a S3: s3://{bucket_name}/{output_key}")
    except Exception as e:
        print(f"Error al subir el archivo JSON a S3: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error al subir el JSON a S3: {e}')
        }

    return {
        'statusCode': 200,
        'body': json.dumps(f'Archivo {file_key} procesado y guardado como {output_key}')
    }
