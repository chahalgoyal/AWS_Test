from playwright.sync_api import Page, expect
import time

class SQSPage:
    def __init__(self, page: Page, region: str = "eu-north-1"):
        self.page = page
        self.region = region
        self.base_url = f"https://{region}.console.aws.amazon.com/sqs/v3/home?region={region}#/queues"

    def navigate(self):
        self.page.goto(self.base_url)
        self.page.wait_for_selector("table", timeout=60000)

    def verify_message_received(self, queue_name: str, expected_text: str):
        self.navigate()
        
        # Click on queue name
        queue_link = self.page.get_by_role("link", name=queue_name, exact=True)
        queue_link.click()
        
        # Click "Send and receive messages"
        self.page.get_by_role("button", name="Send and receive messages").click()
        
        # Click "Poll for messages"
        poll_btn = self.page.get_by_role("button", name="Poll for messages").first
        poll_btn.click()
        
        # Wait a bit for polling
        time.sleep(3)
        
        # Click the first message in the list
        # Sometimes it's a link with the message ID or just clicking the row
        messages_table = self.page.locator("table").nth(1)  # Usually second table on this page
        # Try to click the first message ID link in the table body
        first_message = self.page.locator("table tbody tr td a").first
        first_message.click()
        
        # Verify body
        body_locator = self.page.get_by_text(expected_text)
        expect(body_locator).to_be_visible(timeout=10000)
        
        # Close modal if exists
        close_btn = self.page.get_by_role("button", name="Done")
        if close_btn.count() > 0:
            close_btn.click()

    def verify_message_not_received(self, queue_name: str, unexpected_text: str):
        self.navigate()
        
        queue_link = self.page.get_by_role("link", name=queue_name, exact=True)
        queue_link.click()
        
        self.page.get_by_role("button", name="Send and receive messages").click()
        
        poll_btn = self.page.get_by_role("button", name="Poll for messages").first
        poll_btn.click()
        
        time.sleep(3)
        
        # Verify the unexpected_text is not visible in the DOM
        body_locator = self.page.get_by_text(unexpected_text)
        expect(body_locator).to_be_hidden(timeout=5000)

