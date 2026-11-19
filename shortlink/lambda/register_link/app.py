import boto3
import os
import secrets
import string
from botocore.config import Config
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TOKEN_LENGTH = 6

dynamodb = boto3.resource("dynamodb", config=Config(retries={
    "total_max_attempts": 3,
    "mode": "standard",
}))

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        target_url = body.get("target_url")
        if not target_url:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Bad Request",
                    "message": "Target URL is required",
                }),
                "headers": {
                    "Content-Type": "application/json",
                },
        }
        token = register_link(target_url)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({
                "token": token
            })
        }
    except Exception as e:
        logger.exception(e)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({
                "error": "Internal server error",
            }),
        }

def register_link(target_url: str) -> str:
    table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME"))
    for _ in range(3):
        try:
            token = new_token()
            logger.info(f"Attempting to register {target_url} link with token: {token}")
            table.put_item(
                Item={
                    "token": token,
                    "target_url": target_url,
                },
                ConditionExpression="attribute_not_exists(#token)",
                ExpressionAttributeNames={
                    "#token": "token",
                },
            )
            return token
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            continue 
    raise 

def new_token() -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(TOKEN_LENGTH))