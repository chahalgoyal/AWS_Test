"""
pages/cfn_page.py
All CloudFormation console interactions:
  - Navigate to the Stacks list
  - Create a stack by uploading a local template
  - Poll for CREATE_COMPLETE
  - Read Outputs tab
  - Delete a stack

Selectors confirmed from saved HTML snapshots.
"""

import time
from pathlib import Path
from playwright.sync_api import Page, expect
from .base_page import BasePage


# Base URL pattern for CloudFormation stacks list in a given region
CFN_URL = "https://{region}.console.aws.amazon.com/cloudformation/home?region={region}#/stacks"


class CloudFormationPage(BasePage):
    # ------------------------------------------------------------------ #
    # Dashboard selectors                                                  #
    # ------------------------------------------------------------------ #
    # The "Create stack" button (simple, non-dropdown version confirmed in HTML)
    # Use two fallbacks in case the live page IDs differ.
    CREATE_STACK_BTN_ID   = "button#create-stack-button"
    CREATE_STACK_BTN_TEXT = "button:has-text('Create stack'):not([data-testid*='dropdown'])"

    DELETE_STACK_BTN      = "button#delete-stack-button"

    # ------------------------------------------------------------------ #
    # Create-stack wizard selectors                                        #
    # ------------------------------------------------------------------ #
    # Step 1 — Template source
    UPLOAD_RADIO = "input[value='UPLOAD_TEMPLATE']"
    FILE_INPUT   = "input[type='file']"

    # Step 2 — Stack details
    STACK_NAME_INPUT = "#stackName"

    # Step 4 — Review: IAM capabilities acknowledgment
    # Located by proximity to the acknowledgment text (React-rendered, no stable id)
    IAM_CAPABILITY_LABEL = "I acknowledge that AWS CloudFormation"

    # Wizard navigation
    NEXT_BTN   = "button:has-text('Next')"
    SUBMIT_BTN = "button:has-text('Submit')"

    # ------------------------------------------------------------------ #
    # Stack detail selectors                                               #
    # ------------------------------------------------------------------ #
    OUTPUTS_TAB = "button:has-text('Outputs')"

    # Delete confirmation
    DELETE_CONFIRM_BTN = "button:has-text('Delete')"

    def __init__(self, page: Page, region: str):
        super().__init__(page)
        self.region = region
        self.cfn_url = CFN_URL.format(region=region)

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    def navigate(self) -> None:
        """Open the CloudFormation Stacks list."""
        self.navigate_to(self.cfn_url)

    # ------------------------------------------------------------------ #
    # Create stack                                                         #
    # ------------------------------------------------------------------ #
    def create_stack(self, template_path: str, stack_name: str, acknowledge_iam: bool = False) -> None:
        """
        Walk through the Create Stack wizard:
          1. Click 'Create stack'
          2. Select 'Upload a template file' and upload the YAML
          3. Enter the stack name, leave parameters at template defaults
          4. Skip configure options (just Next)
          5. On Review: check IAM capabilities, then Submit
        """
        # --- Step 0: click the Create Stack button ---
        # Try the stable ID first; fall back to text-based selector
        create_btn = self.page.locator(self.CREATE_STACK_BTN_ID)
        try:
            create_btn.wait_for(state="visible", timeout=10_000)
            create_btn.click()
        except Exception:
            # Fallback: find the last visible button containing "Create stack"
            self.page.get_by_role("button", name="Create stack").last.click()

        self.page.wait_for_load_state("domcontentloaded")
        self.dismiss_cookie_modal()

        # --- Step 1: Template source ---
        # Choose "Upload a template file"
        self.page.locator(self.UPLOAD_RADIO).wait_for(state="visible", timeout=15_000)
        self.page.locator(self.UPLOAD_RADIO).check()

        # Wait for the file input to be available in the DOM, and set the file directly.
        # Playwright can set files on hidden <input type="file"> elements without needing to click the visual button.
        self.page.locator("input[type='file']").set_input_files(str(Path(template_path).resolve()))

        # Small pause to let the S3 upload indicator settle
        self.page.wait_for_timeout(5_000)
        self.page.get_by_role("button", name="Next").last.click()
        self.page.wait_for_load_state("domcontentloaded")

        # --- Step 2: Stack details ---
        self.page.locator(self.STACK_NAME_INPUT).wait_for(state="visible", timeout=15_000)
        self.page.locator(self.STACK_NAME_INPUT).fill(stack_name)

        # Leave all parameters at template defaults
        self.page.get_by_role("button", name="Next").last.click()
        self.page.wait_for_load_state("domcontentloaded")

        # --- Step 3: Configure stack options --- (no changes)
        if acknowledge_iam:
            try:
                self.page.get_by_text("I acknowledge that AWS CloudFormation might create IAM resources.").click(timeout=5000)
            except Exception:
                pass
        self.page.get_by_role("button", name="Next").last.click()
        self.page.wait_for_load_state("domcontentloaded")

        # --- Step 4: Review and create ---
        self._acknowledge_iam_capability()

        self.page.get_by_role("button", name="Submit").click()
        self.page.wait_for_load_state("domcontentloaded")

    def _acknowledge_iam_capability(self) -> None:
        """
        Check the IAM capabilities acknowledgment checkbox on the Review page.
        This checkbox is React-rendered and only appears when the template
        contains IAM resources.  We locate the nearest unchecked checkbox
        to the acknowledgment text.
        """
        try:
            # Wait briefly for the acknowledgment text to appear
            ack = self.page.get_by_text(self.IAM_CAPABILITY_LABEL, exact=False)
            ack.wait_for(state="visible", timeout=5_000)

            # Find the checkbox that is a sibling/descendant near the ack text
            # AWS renders it inside a container with the word 'acknowledge'
            capability_cb = self.page.locator(
                "input[type='checkbox']"
            ).filter(has=self.page.get_by_text("acknowledge", exact=False))

            if capability_cb.count() == 0:
                # Wider search: first unchecked checkbox after the ack text
                # by grabbing all checkboxes not in the cookie banner
                capability_cb = self.page.locator(
                    "input[type='checkbox']:not([id^='awsccc'])"
                ).first

            if not capability_cb.is_checked():
                capability_cb.check()
        except Exception:
            # No IAM capabilities section shown — safe to proceed
            pass

    # ------------------------------------------------------------------ #
    # Status polling                                                       #
    # ------------------------------------------------------------------ #
    def wait_for_create_complete(
        self,
        stack_name: str,
        timeout_seconds: int = 600,
        poll_interval_seconds: int = 15,
    ) -> None:
        """
        Poll the stack list page every `poll_interval_seconds` seconds until
        `CREATE_COMPLETE` appears, or fail immediately on ROLLBACK/FAILED.
        """
        self.navigate()
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(2_000)

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                # Click the AWS UI refresh button to update the React table
                refresh_btn = self.page.locator("button[data-testid='refresh-button']")
                if refresh_btn.is_visible():
                    refresh_btn.click()
                else:
                    self.page.reload()
                self.page.wait_for_timeout(2_000)
            except Exception:
                self.page.reload()
                self.page.wait_for_timeout(2_000)
            
            try:
                # Find the row for this stack in the list
                stack_row = self.page.get_by_role("row", name=stack_name).first
                stack_row.wait_for(state="visible", timeout=5_000)
                row_text = stack_row.inner_text()
            except Exception:
                row_text = ""

            if "CREATE_COMPLETE" in row_text:
                return  # success

            if "ROLLBACK" in row_text or "FAILED" in row_text:
                raise AssertionError(
                    f"Stack '{stack_name}' entered a failure state. "
                    "Check the Events tab in CloudFormation for details."
                )

            print(f"  Stack not yet complete — waiting {poll_interval_seconds}s ...")
            time.sleep(poll_interval_seconds)

        raise TimeoutError(
            f"Stack '{stack_name}' did not reach CREATE_COMPLETE "
            f"within {timeout_seconds} seconds."
        )

    # ------------------------------------------------------------------ #
    # Outputs                                                              #
    # ------------------------------------------------------------------ #
    def get_stack_outputs(self, stack_name: str) -> dict[str, str]:
        """
        Open the stack detail page, click the Outputs tab, and return a dict
        mapping output Key → Value.
        """
        self.navigate()
        self._open_stack(stack_name)

        self.page.locator(self.OUTPUTS_TAB).click()
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(1_500)

        outputs: dict[str, str] = {}
        rows = self.page.locator("table tr").all()
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) >= 2:
                key   = cells[0].inner_text().strip()
                value = cells[1].inner_text().strip()
                if key:
                    outputs[key] = value

        return outputs

    # ------------------------------------------------------------------ #
    # Delete stack                                                         #
    # ------------------------------------------------------------------ #
    def delete_stack(self, stack_name: str, timeout_seconds: int = 600) -> None:
        """
        Select the stack row radio/checkbox, click Delete, confirm, and wait until
        the stack is gone from the list.
        """
        self.navigate()
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(2_000)

        # Select the stack row
        stack_row = self.page.get_by_role("row", name=stack_name).first
        # CFN uses radio buttons for selection, but we'll accept either to be safe
        stack_row.locator("input[type='radio'], input[type='checkbox']").first.check(force=True)
        self.page.wait_for_timeout(1_000)  # Wait for the Delete button to become enabled

        try:
            self.page.locator(self.DELETE_STACK_BTN).click(timeout=5_000)
        except Exception:
            self.page.get_by_role("button", name="Delete stack").first.click()
            
        self.page.wait_for_load_state("domcontentloaded")

        # Confirm the delete dialog
        dialog = self.page.get_by_role("dialog").last
        try:
            dialog.wait_for(state="visible", timeout=10_000)
            # Find the text input and wait for it to be ready  
            confirm_input = dialog.get_by_role("textbox").first
            confirm_input.wait_for(state="visible", timeout=5_000)
            # Use press_sequentially to ensure AWS React UI registers the keystrokes
            confirm_input.clear()
            confirm_input.press_sequentially(stack_name, delay=50)
        except Exception as e:
            print(f"  Note: Could not find or fill confirmation input: {e}")

        # Click the Delete button inside the confirm dialog
        try:
            # Wait a moment for the 'Delete' button to become enabled after typing
            self.page.wait_for_timeout(1000)
            # Locate the button specifically by its testid or role
            confirm_btn = dialog.locator("button[data-testid='delete-stack-button']")
            if confirm_btn.count() == 0:
                confirm_btn = dialog.get_by_role("button", name="Delete").first
            
            confirm_btn.click(timeout=5000)
        except Exception as e:
            print(f"  Fallback clicking delete confirm... {e}")
            self.page.locator(self.DELETE_CONFIRM_BTN).last.click()
            
        self.page.wait_for_load_state("domcontentloaded")

        # Poll until the stack disappears or enters DELETE_COMPLETE
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                # Click the AWS UI refresh button to update the React table
                refresh_btn = self.page.locator("button[data-testid='refresh-button']")
                if refresh_btn.is_visible():
                    refresh_btn.click()
                else:
                    self.page.reload()
                self.page.wait_for_timeout(2_000)
            except Exception:
                self.page.reload()
                self.page.wait_for_timeout(2_000)

            try:
                stack_row = self.page.get_by_role("row", name=stack_name).first
                stack_row.wait_for(state="visible", timeout=5_000)
                row_text = stack_row.inner_text()
            except Exception:
                # Row not found means it disappeared from active list -> deleted
                return
            
            if "DELETE_FAILED" in row_text:
                raise AssertionError(f"Stack '{stack_name}' deletion failed.")
            if "DELETE_COMPLETE" in row_text:
                return  # also success if the list shows it as completely deleted

            print("  Waiting for stack deletion ...")
            time.sleep(15)

        raise TimeoutError(
            f"Stack '{stack_name}' was not deleted within {timeout_seconds} seconds."
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #
    def _open_stack(self, stack_name: str) -> None:
        """Click the stack name link to open its detail page."""
        self.page.get_by_role("link", name=stack_name).first.click()
        self.page.wait_for_load_state("domcontentloaded")
