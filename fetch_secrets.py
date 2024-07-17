import boto3
import os
import json


def get_secret(local=False):
    if not local:
        secret_name = os.getenv("AWS_SECRET_NAME")
        region_name = os.getenv("AWS_REGION_NAME")  # e.g., us-west-2

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)

        # Fetch the secret
        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        except Exception as e:
            raise e

        # Decrypts secret using the associated KMS key.
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
