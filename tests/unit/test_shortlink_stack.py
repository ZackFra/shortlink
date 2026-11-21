import aws_cdk as core
import aws_cdk.assertions as assertions

from shortlink.shortlink_stack import ShortlinkStack

def test_routes():
    app = core.App()
    stack = ShortlinkStack(app, "ShortlinkStack")
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties("AWS::ApiGatewayV2::Route", {
        "RouteKey": "GET /{token}",
        "AuthorizationType": "CUSTOM"
    })

    template.has_resource_properties("AWS::ApiGatewayV2::Route", {
        "RouteKey": "POST /",
        "AuthorizationType": "AWS_IAM"
    })

def test_distribution():
    app = core.App()
    stack = ShortlinkStack(app, "ShortlinkStack")
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": {
            "Aliases": assertions.Match.array_with(["shortlink.hakt.tech"]),
            "DefaultCacheBehavior": {
                "OriginRequestPolicyId": core.aws_cloudfront.OriginRequestPolicy.ALL_VIEWER.origin_request_policy_id
            }
        },
    })