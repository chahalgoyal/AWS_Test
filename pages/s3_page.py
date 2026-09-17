"""
pages/s3_page.py
Verifies S3 bucket existence in the AWS Console.
"""

from playwright.sync_api import Page, expect
from .base_page import BasePage


# S3 is a global service — the bucket list URL does not embed a region
S3_BUCKETS_URL = "https://s3.console.aws.amazon.com/s3/buckets"


class S3Page(BasePage):
    SEARCH_INPUT = "input[placeholder*='Search'], input[aria-label*='Search buckets']"

    def __init__(self, page: Page):
        super().__init__(page)

    def navigate(self) -> None:
        """Open the S3 bucket list."""
        self.navigate_to(S3_BUCKETS_URL)

    def find_bucket(self, bucket_name: str) -> bool:
        """
        Search for the bucket by name and return True if found.

        Args:
            bucket_name: Full bucket name, e.g. 's3-test-123456789012-eu-north-1'.
        Returns:
            True if the bucket link appears on the page.
        """
        self.navigate()
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(2000)

        # Check if the bucket name link appears in the bucket list
        bucket_link = self.page.get_by_role("link", name=bucket_name)
        if bucket_link.count() > 0:
            return True
        
        # Fallback to checking the entire page text
        page_text = self.page.inner_text("body")
        return bucket_name in page_text

    def assert_bucket_exists(self, bucket_name: str) -> None:
        """Assert that the S3 bucket is present in the bucket list."""
        assert self.find_bucket(bucket_name), (
            f"S3 bucket '{bucket_name}' was not found in the bucket list."
        )
