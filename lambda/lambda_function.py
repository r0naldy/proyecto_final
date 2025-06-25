def lambda_handler(event, context):
    import boto3
    import json
    import os

    s3 = boto3.client('s3')
    bucket = os.environ.get('BUCKET_NAME', 'x-bucket')

    for record in event['Records']:
        key = record['s3']['object']['key']
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        # Simula limpieza
        data = json.loads(content)
        data['cleaned'] = True

        new_key = f"cleaned/{key.split('/')[-1]}"
        s3.put_object(Bucket=bucket, Key=new_key, Body=json.dumps(data))

    return {"status": "processedo"}