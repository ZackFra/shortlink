import aws_cdk as core
import aws_cdk.assertions as assertions

from shortlink.shortlink_stack import ShortlinkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in shortlink/shortlink_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ShortlinkStack(app, "shortlink")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
