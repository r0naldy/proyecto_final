import boto3
import csv
import json
import os
import io
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Datos del evento
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key  = event['Records'][0]['s3']['object']['key']

    # Obtener archivo CSV desde S3
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    content = response['Body'].read().decode('utf-8').splitlines()
    reader = csv.DictReader(content)

    cleaned_rows = []

    for row in reader:
        # Regla 1: Eliminar filas vacías
        if all(value.strip() == '' for value in row.values()):
            continue

        # Regla 2: Validar ID no vacío
        if not row['ID']:
            continue

        # Regla 3: Normalizar nombres (capitalización)
        row['Cliente'] = row['Cliente'].strip().title()

        # Regla 4: Validar monto (positivo)
        try:
            monto = float(row['Monto'])
            if monto <= 0:
                continue
            row['Monto'] = round(monto, 2)
        except:
            continue

        # Regla 5: Normalizar campo de ciudad
        row['Ciudad'] = row['Ciudad'].strip().title()

        # Regla 6: Convertir estado a booleano
        estado = row.get('Estado', '').strip().lower()
        row['Estado'] = True if estado in ['activo', 'true', '1'] else False

        # Regla 7: Validar correo (contenga @ y .)
        correo = row.get('Correo', '')
        if '@' not in correo or '.' not in correo:
            continue

        # Regla 8: Normalizar fecha a YYYY-MM-DD
        try:
            fecha = datetime.strptime(row['Fecha'], "%d/%m/%Y")
            row['Fecha'] = fecha.strftime("%Y-%m-%d")
        except:
            continue

        # Regla 9: Eliminar caracteres especiales en notas
        row['Notas'] = ''.join(c for c in row.get('Notas', '') if c.isalnum() or c.isspace())

        # Regla 10: Quitar espacios duplicados en nombre
        row['Cliente'] = ' '.join(row['Cliente'].split())

        # Regla 11: Validar número telefónico (10 dígitos)
        telefono = ''.join(filter(str.isdigit, row.get('Telefono', '')))
        if len(telefono) != 10:
            continue
        row['Telefono'] = telefono

        # Regla 12: Eliminar campos vacíos innecesarios
        row = {k: v for k, v in row.items() if v.strip() != ''}

        # Regla 13: Validar país permitido
        if row.get('Pais', '').strip().lower() not in ['peru', 'chile', 'mexico']:
            continue

        # Regla 14: Estandarizar método de pago
        pago = row.get('Pago', '').strip().lower()
        if pago in ['efectivo', 'cash']:
            row['Pago'] = 'Efectivo'
        elif pago in ['tarjeta', 'card']:
            row['Pago'] = 'Tarjeta'
        elif pago in ['yape', 'plin']:
            row['Pago'] = 'Transferencia'
        else:
            continue

        # Regla 15: Verificar monto < 10000
        if float(row['Monto']) > 10000:
            continue

        # Regla 16: Eliminar campos de debug si existen
        row.pop('debug_info', None)

        # Regla 17: Validar código postal (5 dígitos)
        cp = row.get('CP', '')
        if not cp.isdigit() or len(cp) != 5:
            continue

        # Regla 18: Limitar campo notas a 200 caracteres
        row['Notas'] = row.get('Notas', '')[:200]

        # Regla 19: Asegurar que ID es numérico
        if not row['ID'].isdigit():
            continue

        # Regla 20: Remover duplicados (solo si ID ya fue agregado)
        if any(existing['ID'] == row['ID'] for existing in cleaned_rows):
            continue

        cleaned_rows.append(row)

    # Guardar como JSON en carpeta processed/
    output_filename = os.path.basename(object_key).replace(".csv", ".json")
    output_key = f"processed/{output_filename}"

    s3.put_object(
        Bucket=bucket_name,
        Key=output_key,
        Body=json.dumps(cleaned_rows, indent=2),
        ContentType='application/json'
    )

    return {
        'statusCode': 200,
        'body': f'Se procesó {object_key} y se creó {output_key} con {len(cleaned_rows)} registros limpios.'
    }

#nuevo2