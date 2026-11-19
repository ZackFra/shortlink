import logging
import os
import json
import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", config=Config(retries={
    "total_max_attempts": 3,
    "mode": "standard",
}))

class LinkNotFoundError(Exception):
    pass

def handler(event, context):
    try:
        token = event["pathParameters"]["token"]
        target_url = consume_link(token)
        return {
            "statusCode": 301,
            "headers": {
                "Location": target_url
            }
        }
    except LinkNotFoundError as e:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({
                "error": "Link Not Found",
                "message": f"No link found for this token.",
            }),
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

def consume_link(token: str) -> str:
    table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME"))
    response = table.get_item(
        Key={
            "token": token
        }
    )
    if "Item" not in response:
        raise LinkNotFoundError(f"Link with token {token} not found")
    return response["Item"]["target_url"]