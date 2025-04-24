import boto3
from botocore.config import Config
from dotenv import load_dotenv
from pathlib import Path
import os

endpoint_url = "http://rook-ceph-rgw-ceph-objectstore.rook-ceph.svc:80"

env_path = Path('.') / 'dev_keys.env'
load_dotenv(dotenv_path=env_path)
aws_access_key_id = os.getenv("aws_access_key_id")
aws_secret_access_key = os.getenv("aws_secret_access_key")

BUCKET_NAME = "test-forge"

s3_config = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'}
)

    # Create the boto3 client with the custom endpoint and configuration
s3_client = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    config=s3_config
)

# for listing all of our s3 buckets. 
# if __name__ == "__main__":
#     # Test the connection by listing buckets
#     try:
#         response = s3_client.list_buckets()
#         print("Connected to S3. Buckets:")
#         for bucket in response['Buckets']:
#             print(f"- {bucket['Name']}")
#     except Exception as e:
#         print(f"Error connecting to S3: {e}")
