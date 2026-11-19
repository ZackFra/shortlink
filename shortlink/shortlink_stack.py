from aws_cdk import (
    # Duration,
    Stack,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_authorizers as authorizers,
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigatewayv2_authorizers as authorizers,
    aws_wafv2 as wafv2,
    aws_apigatewayv2_integrations as integrations,
)
from constructs import Construct
from dotenv import load_dotenv
import os

load_dotenv()

if not os.getenv("ORIGIN_VERIFY_SECRET"):
    raise ValueError("ORIGIN_VERIFY_SECRET is not set in .env file")

class ShortlinkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dynamodb_table = dynamodb.Table(self, "ShortlinkTable",
            table_name="shortlinks",
            partition_key=dynamodb.Attribute(name="token", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        verify_origin_lambda = lambda_.Function(self, "VerifyOriginLambda",
            function_name="verify-origin",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="app.handler",
            code=lambda_.Code.from_asset("shortlink/lambda/verify_origin"),
            environment={
                "ORIGIN_VERIFY_SECRET": os.getenv("ORIGIN_VERIFY_SECRET"),
            },
        )

        verify_origin_authorizer = authorizers.HttpLambdaAuthorizer(
            "VerifyOriginAuthorizer", 
            verify_origin_lambda, 
            response_types=[authorizers.HttpLambdaResponseType.SIMPLE],
            identity_source=["$request.header.x-origin-verify"],
        )

        register_link_lambda = lambda_.Function(self, "RegisterLinkLambda",
            function_name="register-link",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="app.handler",
            code=lambda_.Code.from_asset("shortlink/lambda/register_link"),
            environment={
                "DYNAMODB_TABLE_NAME": dynamodb_table.table_name,
            },
        )

        consume_link_lambda = lambda_.Function(self, "ConsumeLinkLambda",
            function_name="consume-link",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="app.handler",
            code=lambda_.Code.from_asset("shortlink/lambda/consume_link"),
            environment={
                "DYNAMODB_TABLE_NAME": dynamodb_table.table_name,
            },
        )

        dynamodb_table.grant_write_data(register_link_lambda)
        dynamodb_table.grant_read_data(consume_link_lambda)

        http_api = apigatewayv2.HttpApi(self, "ShortlinkApi",
            api_name="shortlink-api",
            description="API for the shortlink service",
        )

        http_api.add_routes(
            path="/{token}",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration("ConsumeLinkIntegration", consume_link_lambda),
            authorizer=verify_origin_authorizer,
        )
        
        http_api.add_routes(
            path="/",
            methods=[apigatewayv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("RegisterLinkIntegration", register_link_lambda),
            authorizer=authorizers.HttpIamAuthorizer()
        )

        certificate = acm.Certificate.from_certificate_arn(self, "LinkCert",
            "arn:aws:acm:us-east-1:464948468327:certificate/edc5058e-4dd6-4837-be2f-770b435363bd",
        )

        acl = wafv2.CfnWebACL(self, "LinkAcl",
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="link-hakt-tech",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimit",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=1000,
                            aggregate_key_type="IP",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="rate-limit",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        domain = apigatewayv2.DomainName(self, "LinkDomain",
            domain_name="link.hakt.tech",
            certificate=certificate,
        )

        apigatewayv2.ApiMapping(self, "LinkMapping",
            api=http_api,
            domain_name=domain,
            stage=http_api.default_stage,
        )

        reject_bare_path = cloudfront.Function(self, "RejectBarePath",
            runtime=cloudfront.FunctionRuntime.JS_2_0,
            code=cloudfront.FunctionCode.from_file(
                file_path="shortlink/cloudfront/reject_bare_path.js"
            )
        )

        distribution = cloudfront.Distribution(self, "ShortlinkCdn",
            certificate=certificate,
            web_acl_id=acl.attr_arn,
            domain_names=["link.hakt.tech"],
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    domain.regional_domain_name,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    custom_headers={"X-Origin-Verify": os.getenv("ORIGIN_VERIFY_SECRET")}
                ),
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                function_associations=[cloudfront.FunctionAssociation(
                    function=reject_bare_path,
                    event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                )],
            ),
        )