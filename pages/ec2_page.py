"""
pages/ec2_page.py
Verifies EC2 instance existence in the AWS Console.
"""

from playwright.sync_api import Page, expect
from .base_page import BasePage


EC2_INSTANCES_URL = (
    "https://{region}.console.aws.amazon.com/ec2/home?region={region}#Instances:"
)


class EC2Page(BasePage):
    SEARCH_INPUT    = "input[placeholder*='Search'], input[aria-label*='Search']"
    INSTANCE_STATE  = "td:has-text('running'), td:has-text('stopped'), td:has-text('pending')"

    def __init__(self, page: Page, region: str):
        super().__init__(page)
        self.region = region

    def navigate(self) -> None:
        """Open the EC2 Instances list."""
        url = EC2_INSTANCES_URL.format(region=self.region)
        self.navigate_to(url)

    def find_instance(self, instance_id: str) -> bool:
        """
        Search for the instance by its ID and return True if found in a
        non-terminated state (running, stopped, or pending).

        Args:
            instance_id: The EC2 instance ID, e.g. 'i-0abc123'.
        Returns:
            True if found, False if not visible.
        """
        self.navigate()

        # Use the search bar to filter by instance ID
        search = self.page.locator(self.SEARCH_INPUT).first
        search.fill(instance_id)
        self.page.keyboard.press("Enter")
        
        try:
            # Wait up to 20 seconds for the instance ID to appear anywhere on the page
            self.page.get_by_text(instance_id).first.wait_for(state="visible", timeout=20000)
        except Exception:
            return False

        # Extract the page text and find the proximity context of our instance
        page_text = self.page.inner_text("body")
        idx = page_text.find(instance_id)
        if idx != -1:
            # The EC2 state (e.g. "Running", "Terminated") appears in the columns immediately 
            # following the instance ID. We check the next 150 characters.
            context = page_text[idx:idx+150].lower()
            return "terminated" not in context
            
        return False

    def assert_instance_exists(self, instance_id: str) -> None:
        """Assert that an instance with the given ID exists and is not terminated."""
        assert self.find_instance(instance_id), (
            f"EC2 instance '{instance_id}' was not found or is terminated."
        )
