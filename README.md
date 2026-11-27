# shortlink

A URL shortener at `https://shortlink.hakt.tech`. Creating a link requires an AWS signature. Visiting a short link redirects to the stored URL.

`POST /` stores a target URL and returns a 6-character token. `GET /{token}` responds with `301` and a `Location` header. Tokens are random and stored in DynamoDB. CloudFront serves `shortlink.hakt.tech`, checks that a `GET` path is a single token, and rate-limits viewers. API Gateway only accepts redirect traffic that came through that distribution.

## Layout

| Path | Role |
|---|---|
| `shortlink/shortlink_stack.py` | CDK stack |
| `shortlink/lambda/register_link` | `POST /`, IAM auth |
| `shortlink/lambda/consume_link` | `GET /{token}`, returns the redirect |
| `shortlink/lambda/verify_origin` | Checks the CloudFront origin header |
| `shortlink/cloudfront/reject_bare_path.js` | Rejects `GET` paths that are not a token |

## Setup

The stack deploys in `us-east-1`. The CloudFront certificate and the web ACL both have to live there. The certificate ARN and the domain name are set in `shortlink/shortlink_stack.py`. DNS for `link.hakt.tech` is a CNAME to the distribution, DNS-only, so viewers reach CloudFront rather than Cloudflare.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install python-dotenv
```

Create a `.env` file in the repository root. It is gitignored.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```
ORIGIN_VERIFY_SECRET=<that value>
```

CDK reads it when synthesizing. The same value is sent by CloudFront and checked by the origin authorizer. Bootstrap the account once:

```bash
cdk bootstrap --region us-east-1
cdk deploy --region us-east-1
```

## API

Create a link with [awscurl](https://github.com/okigan/awscurl). The caller needs `execute-api:Invoke` in the API account. `--region` is `us-east-1` because that is where the API is deployed, even though the URL is the custom domain.

```bash
awscurl --profile <profile> --service execute-api --region us-east-1 \
  -X POST \
  -H "content-type: application/json" \
  -d '{"target_url":"https://example.com"}' \
  "https://shortlink.hakt.tech/"
```

```json
{"token": "aB3xY9"}
```

Open `https://shortlink.hakt.tech/aB3xY9`. A path that is not six letters or digits is rejected at CloudFront. An unknown token is a `404`.

## Commands

* `cdk synth` emit the CloudFormation template
* `cdk diff` compare the deployed stack with the current code
* `cdk deploy --region us-east-1` deploy
