"""
conftest.py
Pytest fixtures shared across the entire test suite.

Browser lifecycle is managed entirely here using sync_playwright() directly.
We do NOT depend on any pytest-playwright fixtures (browser / context / page)
to avoid the TargetClosedError cascade that occurs when the plugin's
function-scoped teardown interferes with our session-scoped page object.

All fixtures that need a browser are named aws_* to make the ownership clear.
"""

import csv
import pytest
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from config import USERNAME, PASSWORD, SIGN_IN_URL, TEMPLATE_FILE, REGION, STACK_NAME
from pages.login_page import LoginPage
from pages.cfn_page import CloudFormationPage
from pages.ec2_page import EC2Page
from pages.s3_page import S3Page
from pages.lambda_page import LambdaPage




# ---------------------------------------------------------------------------
# Playwright / browser / context / page  — entirely self-managed
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def aws_playwright() -> Playwright:
    """Start a Playwright instance for the whole session."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def aws_browser(aws_playwright: Playwright) -> Browser:
    """
    Launch a headed Chromium browser for the session.
    headless=False keeps the browser window visible.
    """
    browser = aws_playwright.chromium.launch(headless=False)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def aws_context(aws_browser: Browser) -> BrowserContext:
    """
    One browser context (cookie jar) for the entire session.
    All AWS console cookies set during login persist here.
    """
    ctx = aws_browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture(scope="session")
def aws_page(aws_context: BrowserContext) -> Page:
    """
    One Playwright page for the entire session.
    All page objects share this tab so login state is preserved.
    """
    pg = aws_context.new_page()
    yield pg
    pg.close()


# ---------------------------------------------------------------------------
# Page-object fixtures  (session-scoped, all share aws_page)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def login_page(aws_page: Page) -> LoginPage:
    return LoginPage(aws_page, sign_in_url=SIGN_IN_URL)

@pytest.fixture(scope="session", autouse=True)
def authenticate_session(login_page: LoginPage) -> None:
    """
    Automatically log in to the AWS console once per session.
    All subsequent tests will share this authenticated state.
    """
    login_page.navigate()
    # Check if we're already logged in (e.g. if state was somehow restored)
    try:
        login_page.assert_logged_in()
        return
    except Exception:
        pass
        
    login_page.login(
        username=USERNAME,
        password=PASSWORD,
    )
    login_page.assert_logged_in()


@pytest.fixture(scope="session")
def cfn_page(aws_page: Page) -> CloudFormationPage:
    return CloudFormationPage(aws_page, region=REGION)


@pytest.fixture(scope="session")
def ec2_page(aws_page: Page) -> EC2Page:
    return EC2Page(aws_page, region=REGION)


@pytest.fixture(scope="session")
def s3_page(aws_page: Page) -> S3Page:
    return S3Page(aws_page)


@pytest.fixture(scope="session")
def lambda_page(aws_page: Page) -> LambdaPage:
    return LambdaPage(aws_page, region=REGION)


@pytest.fixture(scope="session")
def sns_page(aws_page: Page) -> SNSPage:
    from pages.sns_page import SNSPage
    return SNSPage(aws_page, region=REGION)


@pytest.fixture(scope="session")
def sqs_page(aws_page: Page) -> SQSPage:
    from pages.sqs_page import SQSPage
    return SQSPage(aws_page, region=REGION)



# ---------------------------------------------------------------------------
# Shared state bag
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def stack_info() -> dict:
    """
    Mutable dict carrying resource IDs from the CFN Outputs tab into
    the EC2 / S3 / Lambda verification tests.
    """
    return {
        "ec2_instance_id": None,
        "s3_bucket_name":  None,
        "lambda_url":      None,
    }
