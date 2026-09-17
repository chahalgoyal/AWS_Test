"""
pages/lambda_page.py
Verifies Lambda function existence in the AWS Console.
"""

from playwright.sync_api import Page, expect
from .base_page import BasePage


LAMBDA_URL = (
    "https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions"
)


class LambdaPage(BasePage):
    SEARCH_INPUT = "input[type='search']:not([readonly])"

    def __init__(self, page: Page, region: str):
        super().__init__(page)
        self.region = region

    def navigate(self) -> None:
        """Open the Lambda Functions list."""
        url = LAMBDA_URL.format(region=self.region)
        self.navigate_to(url)

    def find_function(self, function_name: str) -> bool:
        """
        Search for the Lambda function by name and return True if found.

        Args:
            function_name: The exact function name, e.g. 'lambda_test'.
        Returns:
            True if the function link appears on the page.
        """
        self.navigate()

        # Use the search input to filter functions
        search = self.page.locator(self.SEARCH_INPUT).first
        search.fill(function_name)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(3000)

        # Use the exact link match instead of inner_text, because inner_text
        # contains the search query and empty state messages (e.g. "No results for X").
        return self.page.get_by_role("link", name=function_name, exact=True).is_visible()

    def assert_function_exists(self, function_name: str) -> None:
        """Assert that the Lambda function is present in the function list."""
        assert self.find_function(function_name), (
            f"Lambda function '{function_name}' was not found in the functions list."
        )
