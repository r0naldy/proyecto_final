#!/bin/bash
sudo apt update -y
sudo apt install python3-pip -y
pip3 install flask boto3

cat <<EOF > /home/ubuntu/app.py
from flask import Flask, jsonify
import boto3
import json

app = Flask(__name__)
s3 = boto3.client('s3')
BUCKET = 'x-bucket'

@app.route('/data-json-<file_id>', methods=['GET'])
def get_file(file_id):
    key = f"cleaned/{file_id}.json"
    response = s3.get_object(Bucket=BUCKET, Key=key)
    data = json.loads(response['Body'].read())
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
EOF

nohup python3 /home/ubuntu/app.py &
