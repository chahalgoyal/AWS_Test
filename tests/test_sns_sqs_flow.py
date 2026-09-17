import pytest
from pages.login_page import LoginPage
from pages.cfn_page import CloudFormationPage
from pages.sns_page import SNSPage
from pages.sqs_page import SQSPage
from config import REGION
import time

from pathlib import Path
STACK_NAME = "sns-sqs-test-stack"
TEMPLATE_FILE = Path(__file__).parent.parent / "sns_sqs_template.yaml"
TEMPLATE_PATH = str(TEMPLATE_FILE)

# Login is handled by autouse fixture in conftest.py

def test_cfn_create_stack(cfn_page: CloudFormationPage) -> None:
    cfn_page.navigate()
    cfn_page.create_stack(
        template_path=TEMPLATE_PATH,
        stack_name=STACK_NAME,
        acknowledge_iam=False
    )

def test_cfn_stack_create_complete(cfn_page: CloudFormationPage) -> None:
    cfn_page.wait_for_create_complete(
        stack_name=STACK_NAME,
        timeout_seconds=600,
        poll_interval_seconds=15,
    )

def test_cfn_outputs_captured(cfn_page: CloudFormationPage, stack_info: dict) -> None:
    outputs = cfn_page.get_stack_outputs(STACK_NAME)
    stack_info["sns_topic_arn"] = outputs.get("TopicArn")
    stack_info["sqs_queue_url"] = outputs.get("QueueUrl")
    
    # Deriving names from ARN / URL for navigation
    # Topic ARN format: arn:aws:sns:region:account_id:TopicName
    # Queue URL format: https://sqs.region.amazonaws.com/account_id/QueueName
    stack_info["sns_topic_name"] = stack_info["sns_topic_arn"].split(":")[-1]
    stack_info["sqs_queue_name"] = stack_info["sqs_queue_url"].split("/")[-1]

def test_publish_sns_message(sns_page: SNSPage, stack_info: dict) -> None:
    topic_name = stack_info["sns_topic_name"]
    message_body = "Hello from Playwright - SNS to SQS Verification"
    attributes = {"message_type": "test_alert"}
    
    sns_page.publish_message(topic_name, message_body, attributes)

def test_verify_sqs_message(sqs_page: SQSPage, stack_info: dict) -> None:
    queue_name = stack_info["sqs_queue_name"]
    expected_text = "Hello from Playwright - SNS to SQS Verification"
    
    sqs_page.verify_message_received(queue_name, expected_text)

def test_publish_sns_message_filtered_out(sns_page: SNSPage, stack_info: dict) -> None:
    topic_name = stack_info["sns_topic_name"]
    message_body = "This message should be filtered out!"
    # The subscription filter policy requires message_type: test_alert
    attributes = {"message_type": "ignore_me"}
    
    sns_page.publish_message(topic_name, message_body, attributes)

def test_verify_sqs_message_not_received(sqs_page: SQSPage, stack_info: dict) -> None:
    queue_name = stack_info["sqs_queue_name"]
    unexpected_text = "This message should be filtered out!"
    
    sqs_page.verify_message_not_received(queue_name, unexpected_text)

def test_cfn_teardown(cfn_page: CloudFormationPage) -> None:
    cfn_page.delete_stack(
        stack_name=STACK_NAME,
        timeout_seconds=600,
    )
