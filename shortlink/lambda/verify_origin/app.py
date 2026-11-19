import os
import hmac

def handler(event, context):
    expected = os.environ["ORIGIN_VERIFY_SECRET"]
    got = (event.get("headers") or {}).get("x-origin-verify", "")
    return {"isAuthorized": hmac.compare_digest(got, expected)}