import json
import boto3
import pandas as pd
import io
import re
import unicodedata

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Obtener nombre del bucket y archivo
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Descargar archivo CSV desde S3
    response = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(response['Body'])

    # REGULAS DE NEGOCIO (20)

    # 1. QUANTITYORDERED vacíos → eliminar
    df = df.dropna(subset=["QUANTITYORDERED"])

    # 2. PRICEEACH negativos → NaN
    df["PRICEEACH"] = pd.to_numeric(df["PRICEEACH"], errors='coerce')
    df.loc[df["PRICEEACH"] < 0, "PRICEEACH"] = pd.NA

    # 3. STATUS mal escrito → corregir
    df["STATUS"] = df["STATUS"].replace({"DLEIVERED": "DELIVERED"})

    # 4. ORDERDATE inválidas → descartar
    df["ORDERDATE"] = pd.to_datetime(df["ORDERDATE"], errors='coerce')
    df = df.dropna(subset=["ORDERDATE"])

    # 5. SALES texto → convertir o eliminar
    df["SALES"] = pd.to_numeric(df["SALES"], errors='coerce')
    df = df.dropna(subset=["SALES"])

    # 6. Eliminar duplicados
    df = df.drop_duplicates()

    # 7. PRODUCTCODE muy largo → truncar a 15
    df["PRODUCTCODE"] = df["PRODUCTCODE"].astype(str).str.slice(0, 15)

    # 8. ORDERNUMBER vacío → eliminar
    df = df.dropna(subset=["ORDERNUMBER"])

    # 9. ORDERLINENUMBER vacío → eliminar
    df = df.dropna(subset=["ORDERLINENUMBER"])

    # 10. QUANTITYORDERED = 0 → eliminar
    df = df[df["QUANTITYORDERED"] != 0]

    # 11. SALES vacíos → eliminar (ya cubierto en regla 5)

    # 12. ORDERDATE texto irreconocible → descartado (ya cubierto en regla 4)

    # 13. PRODUCTLINE muy largo → truncar a 30
    df["PRODUCTLINE"] = df["PRODUCTLINE"].astype(str).str.slice(0, 30)

    # 14. NUMERICCODE con texto tipo "abc", "xx" → filtrar
    df["NUMERICCODE"] = pd.to_numeric(df["NUMERICCODE"], errors='coerce')
    df = df.dropna(subset=["NUMERICCODE"])

    # 15. STATUS vacío → colocar "UNKNOWN"
    df["STATUS"] = df["STATUS"].fillna("UNKNOWN")

    # 16. PRICEEACH no numérico → convertir o eliminar (ya cubierto en regla 2)

    # 17. ORDERNUMBER tipo string "ORDX" → eliminar si no es número
    df = df[df["ORDERNUMBER"].astype(str).str.isnumeric()]

    # 18. ORDERLINENUMBER tipo "LINEA-X" → descartar
    df = df[df["ORDERLINENUMBER"].astype(str).str.isnumeric()]

    # 19. COUNTRY con emojis → limpiar
    def remove_emojis(text):
        if pd.isnull(text):
            return text
        return ''.join(c for c in text if not unicodedata.category(c).startswith('So'))

    df["COUNTRY"] = df["COUNTRY"].apply(remove_emojis)

    # 20. CITY vacío → "SIN CIUDAD"
    df["CITY"] = df["CITY"].fillna("SIN CIUDAD")

    # Guardar resultado como JSON
    json_buffer = io.StringIO()
    df.to_json(json_buffer, orient="records", force_ascii=False)

    result_key = key.replace("raw/", "processed/").replace(".csv", ".json")

    s3.put_object(
        Bucket=bucket,
        Key=result_key,
        Body=json_buffer.getvalue(),
        ContentType="application/json"
    )

    return {
        'statusCode': 200,
        'body': f'Datos procesados y guardados como {result_key}'
    }
# activando workflow por prueba