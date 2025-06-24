import json
import boto3
import pandas as pd
import io
import re

s3 = boto3.client("s3")
bucket_name = "x-bucket-cloud"

def clean_data(df):
    # 1. QUANTITYORDERED: Vacíos → eliminar o asignar valor por defecto
    df = df[df['QUANTITYORDERED'].notnull()]
    
    # 2. PRICEEACH: Negativos → poner como NaN
    df.loc[df['PRICEEACH'] < 0, 'PRICEEACH'] = pd.NA

    # 3. STATUS: Corregir errores comunes
    df['STATUS'] = df['STATUS'].replace({'DLEIVERED': 'DELIVERED'})

    # 4. ORDERDATE: Fechas inválidas → descartar
    df['ORDERDATE'] = pd.to_datetime(df['ORDERDATE'], errors='coerce')
    df = df[df['ORDERDATE'].notnull()]

    # 5. SALES: Texto → convertir a número o descartar
    df['SALES'] = pd.to_numeric(df['SALES'], errors='coerce')
    df = df[df['SALES'].notnull()]

    # 6. Eliminar duplicados
    df = df.drop_duplicates()

    # 7. PRODUCTCODE: Truncar a 15 caracteres
    df['PRODUCTCODE'] = df['PRODUCTCODE'].astype(str).str[:15]

    # 8-9. ORDERNUMBER y ORDERLINENUMBER: Vacíos → eliminar
    df = df[df['ORDERNUMBER'].notnull() & df['ORDERLINENUMBER'].notnull()]

    # 10. QUANTITYORDERED: Ceros → eliminar
    df = df[df['QUANTITYORDERED'] != 0]

    # 11. SALES: Vacíos → descartar (ya cubierto en 5)

    # 12. ORDERDATE: Texto irreconocible → ya descartado en 4

    # 13. PRODUCTLINE: Truncar a 30 caracteres
    df['PRODUCTLINE'] = df['PRODUCTLINE'].astype(str).str[:30]

    # 14. NUMERICCODE: Eliminar texto no numérico
    df = df[df['NUMERICCODE'].astype(str).str.isnumeric()]

    # 15. STATUS: Null → colocar "UNKNOWN"
    df['STATUS'] = df['STATUS'].fillna("UNKNOWN")

    # 16. PRICEEACH: Texto → convertir a número o eliminar
    df['PRICEEACH'] = pd.to_numeric(df['PRICEEACH'], errors='coerce')
    df = df[df['PRICEEACH'].notnull()]

    # 17. ORDERNUMBER: string tipo "ORDX" → invalidar si no es numérico
    df = df[df['ORDERNUMBER'].astype(str).str.isnumeric()]

    # 18. ORDERLINENUMBER: texto tipo "LINEA-X" → descartar
    df = df[~df['ORDERLINENUMBER'].astype(str).str.contains("LINEA-", na=False)]

    # 19. COUNTRY: quitar emojis
    df['COUNTRY'] = df['COUNTRY'].astype(str).apply(lambda x: re.sub(r'[^\w\s,.-]', '', x))

    # 20. CITY: Vacíos → "SIN CIUDAD"
    df['CITY'] = df['CITY'].fillna("SIN CIUDAD")

    return df

def lambda_handler(event, context):
    # Obtener nombre del archivo desde el evento
    key = event['Records'][0]['s3']['object']['key']
    print(f"📥 Procesando archivo: {key}")

    # Leer CSV desde S3
    obj = s3.get_object(Bucket=bucket_name, Key=key)
    data = obj['Body'].read()
    df = pd.read_csv(io.BytesIO(data))

    # Limpiar datos
    clean_df = clean_data(df)

    # Convertir a JSON
    result = clean_df.to_dict(orient="records")
    json_data = json.dumps(result, indent=2)

    # Definir nuevo nombre
    output_key = key.replace("raw/", "processed/").replace(".csv", ".json")

    # Guardar JSON limpio en S3
    s3.put_object(Body=json_data, Bucket=bucket_name, Key=output_key)
    print(f"✅ Archivo limpio guardado en: s3://{bucket_name}/{output_key}")

    return {
        'statusCode': 200,
        'body': f"Archivo procesado y guardado: {output_key}"
    }
