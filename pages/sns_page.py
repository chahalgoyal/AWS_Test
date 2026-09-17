from playwright.sync_api import Page, expect
import time

class SNSPage:
    def __init__(self, page: Page, region: str = "eu-north-1"):
        self.page = page
        self.region = region
        self.base_url = f"https://{region}.console.aws.amazon.com/sns/v3/home?region={region}#/topics"

    def navigate(self):
        self.page.goto(self.base_url)
        # Wait for the topics table to load
        self.page.wait_for_selector("table", timeout=60000)

    def publish_message(self, topic_name: str, message_body: str, attributes: dict = None):
        """Navigate to a topic and publish a message with attributes."""
        self.navigate()
        
        # Click on the topic link in the table
        # Since AWS console tables use links for names, we can click the exact text
        topic_link = self.page.get_by_role("link", name=topic_name, exact=True)
        topic_link.click()
        
        # Click Publish message button
        publish_btn = self.page.get_by_role("button", name="Publish message")
        publish_btn.click()
        
        # We are on the publish message page
        # Fill message body
        # The body might be a textarea
        self.page.get_by_role("textbox", name="Message body").fill(message_body)
        
        if attributes:
            for i, (key, val) in enumerate(attributes.items()):
                # Add message attribute
                # Usually there's a section or button for adding attributes
                # In AWS Console, there might be 'Message attributes' accordion and 'Add new attribute' button
                # Or it might be visible already. We will try to find and click it if not visible.
                
                # Expand 'Message attributes' if collapsed
                # Actually, typically it's open or has a button.
                # Let's just look for "Message attributes" heading or button
                try:
                    self.page.get_by_role("button", name="Message attributes").click()
                except:
                    pass
                
                # It might have name, type, value inputs
                # Using general selectors for the first attribute row
                # In AWS UI, it's a dropdown button
                type_btn = self.page.locator("button", has_text="Select attribute type").first
                type_btn.click()
                self.page.wait_for_timeout(1000)
                self.page.get_by_role("option", name="String", exact=True).click()
                     
                name_inputs = self.page.get_by_role("textbox", name="Name")
                if name_inputs.count() > 0:
                     name_inputs.nth(i).fill(key)
                     
                value_inputs = self.page.get_by_role("textbox"  , name="Value")
                if value_inputs.count() > 0:
                     value_inputs.nth(i).fill(val)
                     
        # Click final Publish message button
        # There might be two buttons named "Publish message", one at top, one at bottom
        self.page.get_by_role("button", name="Publish message").last.click()
        
        # Verify success message
        expect(self.page.get_by_text("Message published to topic", exact=False)).to_be_visible(timeout=15000)
