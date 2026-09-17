"""
tests/test_cfn_stack.py
End-to-end test suite for the CloudFormation stack deployment and service verification.

Test order (run sequentially):
  1. test_login                    — sign into the AWS Console
  2. test_cfn_create_stack         — upload template and submit the Create Stack wizard
  3. test_cfn_stack_create_complete— poll until CREATE_COMPLETE
  4. test_cfn_outputs_captured     — read Outputs tab and store resource IDs
  5. test_ec2_instance_exists      — verify EC2 instance in the EC2 console
  6. test_s3_bucket_exists         — verify S3 bucket in the S3 console
  7. test_lambda_function_exists   — verify Lambda function in the Lambda console
  8. test_cfn_teardown             — delete the stack and wait for deletion

All tests share a single browser session (no re-login between tests).
"""

import pytest

from pages.cfn_page import CloudFormationPage
from pages.ec2_page import EC2Page
from pages.s3_page import S3Page
from pages.lambda_page import LambdaPage
from config import TEMPLATE_FILE, STACK_NAME, REGION

# Resource names as defined in the CFN template defaults
EC2_NAME_TAG   = "ec2_test"
LAMBDA_NAME    = "lambda_test"

# S3 bucket name: "${S3Name}-${AWS::AccountId}-${AWS::Region}"
# AccountId confirmed from saved HTML snapshots: 121356473796
S3_BUCKET_NAME = f"s3-test-121356473796-{REGION}"

TEMPLATE_PATH  = str(TEMPLATE_FILE)


# 1. Login handled by autouse fixture in conftest.py


# ===========================================================================
# 2. Create the CloudFormation stack
# ===========================================================================

def test_cfn_create_stack(cfn_page: CloudFormationPage) -> None:
    """
    Open CloudFormation, start the Create Stack wizard, upload template.yaml,
    enter the stack name, acknowledge IAM capabilities, and submit.
    """
    cfn_page.navigate()
    cfn_page.create_stack(
        template_path=TEMPLATE_PATH,
        stack_name=STACK_NAME,
        acknowledge_iam=True
    )

    # After submitting we should be on the stack detail page showing an
    # in-progress status.
    page_text = cfn_page.page.inner_text("body")
    assert "CREATE_IN_PROGRESS" in page_text or STACK_NAME in page_text, (
        "Stack creation submission did not navigate to the expected stack detail page."
    )


# ===========================================================================
# 3. Wait for CREATE_COMPLETE
# ===========================================================================
def test_cfn_stack_create_complete(cfn_page: CloudFormationPage) -> None:
    """
    Poll the stack status every 15 seconds (up to 10 minutes) until
    CREATE_COMPLETE is reached. Fails immediately on ROLLBACK/FAILED.
    """
    cfn_page.wait_for_create_complete(
        stack_name=STACK_NAME,
        timeout_seconds=600,
        poll_interval_seconds=15,
    )

# ===========================================================================
# 3b. CFN Negative Test: Duplicate Stack Name
# ===========================================================================
def test_cfn_create_duplicate_stack(cfn_page: CloudFormationPage) -> None:
    """
    Attempt to create a stack with the same name and verify the UI validation error.
    """
    from playwright.sync_api import expect
    cfn_page.navigate()
    
    # Click Create stack
    create_btn = cfn_page.page.locator(cfn_page.CREATE_STACK_BTN_ID)
    try:
        create_btn.wait_for(state="visible", timeout=10_000)
        create_btn.click()
    except Exception:
        cfn_page.page.get_by_role("button", name="Create stack").last.click()

    # If it's a dropdown, click "With new resources (standard)"
    try:
        cfn_page.page.get_by_text("With new resources (standard)").click(timeout=3000)
    except Exception:
        pass

    cfn_page.page.wait_for_load_state("domcontentloaded")
    cfn_page.page.locator(cfn_page.UPLOAD_RADIO).wait_for(state="visible", timeout=15_000)
    cfn_page.page.locator(cfn_page.UPLOAD_RADIO).check()

    # Upload template
    from pathlib import Path
    cfn_page.page.locator("input[type='file']").set_input_files(str(Path(TEMPLATE_PATH).resolve()))
    cfn_page.page.wait_for_timeout(3_000)
    cfn_page.page.get_by_role("button", name="Next").last.click()
    
    # Step 2: Stack details
    cfn_page.page.locator(cfn_page.STACK_NAME_INPUT).wait_for(state="visible", timeout=15_000)
    cfn_page.page.locator(cfn_page.STACK_NAME_INPUT).fill(STACK_NAME)
    
    # Click Next to trigger the "already exists" validation error
    cfn_page.page.get_by_role("button", name="Next").last.click()
    
    # It should show a validation error because stack name exists
    # Wait for the inline validation error to appear
    expect(cfn_page.page.get_by_text("already exists", exact=False).first).to_be_visible(timeout=10000)
    
    # Click Cancel to exit wizard
    cfn_page.page.get_by_role("button", name="Cancel").click()


# ===========================================================================
# 4. Capture CFN Outputs
# ===========================================================================
def test_cfn_outputs_captured(
    cfn_page: CloudFormationPage,
    stack_info: dict,
) -> None:
    """
    Open the Outputs tab of the created stack and store the resource IDs
    in the shared `stack_info` dict for subsequent tests.

    Expected output keys (from template.yaml):
        EC2InstanceId   → instance ID (e.g. i-0abc123...)
        S3BucketName    → full bucket name
        PublicLambdaUrl → function URL
    """
    outputs = cfn_page.get_stack_outputs(STACK_NAME)

    assert "EC2InstanceId" in outputs,   f"EC2InstanceId missing from outputs: {outputs}"
    assert "S3BucketName" in outputs,    f"S3BucketName missing from outputs: {outputs}"
    assert "PublicLambdaUrl" in outputs, f"PublicLambdaUrl missing from outputs: {outputs}"

    stack_info["ec2_instance_id"] = outputs["EC2InstanceId"]
    stack_info["s3_bucket_name"]  = outputs["S3BucketName"]
    stack_info["lambda_url"]      = outputs["PublicLambdaUrl"]

    print(f"\n  EC2 Instance ID : {stack_info['ec2_instance_id']}")
    print(f"  S3 Bucket Name  : {stack_info['s3_bucket_name']}")
    print(f"  Lambda URL      : {stack_info['lambda_url']}")


# ===========================================================================
# 5. Verify EC2 Instance
# ===========================================================================
def test_ec2_instance_exists(
    ec2_page: EC2Page,
    stack_info: dict,
) -> None:
    """
    Navigate to the EC2 Instances console and confirm the instance created
    by the CFN stack exists and is NOT in a terminated state.
    """
    instance_id = stack_info["ec2_instance_id"]
    assert instance_id, "EC2 instance ID was not captured from CFN outputs."

    ec2_page.assert_instance_exists(instance_id)


# ===========================================================================
# 6. Verify S3 Bucket
# ===========================================================================
def test_s3_bucket_exists(
    s3_page: S3Page,
    stack_info: dict,
) -> None:
    """
    Navigate to the S3 Buckets console and confirm the bucket created
    by the CFN stack is present in the list.
    """
    bucket_name = stack_info["s3_bucket_name"] or S3_BUCKET_NAME
    s3_page.assert_bucket_exists(bucket_name)


# ===========================================================================
# 7. Verify Lambda Function
# ===========================================================================
def test_lambda_function_exists(stack_info: dict) -> None:
    """
    Call the Lambda function via its Public URL to confirm it works
    and print the output.
    """
    lambda_url = stack_info.get("lambda_url")
    assert lambda_url, "Lambda URL was not captured from CFN outputs."

    import urllib.request
    print(f"\\n  Calling Lambda at: {lambda_url}")
    
    req = urllib.request.Request(lambda_url)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            assert status_code == 200, f"Lambda returned status {status_code}"
            print(f"  Lambda response ({status_code}): {body}")
    except Exception as e:
        import pytest
        pytest.fail(f"Failed to call Lambda URL '{lambda_url}': {e}")


# ===========================================================================
# 7b. Lambda Negative Test: Function does not exist
# ===========================================================================
def test_lambda_function_not_exists(lambda_page: LambdaPage) -> None:
    """
    Search for a non-existent Lambda function and verify it is not found.
    """
    fake_name = "non_existent_lambda_function_999"
    found = lambda_page.find_function(fake_name)
    assert not found, f"Expected not to find fake function '{fake_name}', but it was found."


# ===========================================================================
# 8. Teardown — delete the stack
# ===========================================================================

def test_cfn_teardown(cfn_page: CloudFormationPage) -> None:
    """
    Select the stack in the CFN console, initiate deletion, and wait until
    the stack is fully removed from the stack list.
    """
    cfn_page.delete_stack(
        stack_name=STACK_NAME,
        timeout_seconds=600,
    )
