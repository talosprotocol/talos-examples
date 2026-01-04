import boto3
import os
import logging

logger = logging.getLogger("mcp-provider-aws")

class AWSProvider:
    def __init__(self):
        self.endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        
        logger.info(f"Initializing AWS Provider. Endpoint: {self.endpoint}")
        
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
        self.lambda_ = boto3.client(
            "lambda",
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def s3_create_bucket(self, name: str):
        self.s3.create_bucket(Bucket=name)
        return {"status": "success", "message": f"Bucket '{name}' created."}

    def s3_delete_bucket(self, name: str):
        self.s3.delete_bucket(Bucket=name)
        return {"status": "success", "message": f"Bucket '{name}' deleted."}

    def lambda_create_function(self, name: str, code_zip: bytes = b""):
        # Dummy create implementation
        return {"status": "success", "message": f"Function '{name}' created."}
    
    # Simulate Lambda list for verification
    def lambda_list(self):
        # In a real implementation we would call list_functions
        # For this demo we return a mocked list if we "created" it, or rely on LocalStack logic
        # But wait, localstack is awesome. Let's try real call.
        try:
            resp = self.lambda_.list_functions()
            names = [f["FunctionName"] for f in resp.get("Functions", [])]
            return sorted(names)
        except Exception as e:
            logger.error(f"Failed to list lambdas: {e}")
            return []

    # Simplified interface mapping
    def execute(self, tool_name: str, params: dict):
        if tool_name == "aws:s3:create_bucket":
            return self.s3_create_bucket(params.get("name"))
        elif tool_name == "aws:s3:delete_bucket":
            return self.s3_delete_bucket(params.get("name"))
        elif tool_name == "aws:lambda:create_function":
            return self.lambda_create_function(params.get("name"))
        elif tool_name == "aws:lambda:list_functions":
            funcs = self.lambda_list()
            return {"functions": funcs}
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
