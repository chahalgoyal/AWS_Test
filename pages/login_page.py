"""
pages/login_page.py
Handles the AWS IAM Console sign-in page.

Selectors confirmed from saved HTML snapshot:
  Username  → <input id="username">
  Password  → <input id="password">
  Submit    → <button id="signin_button">
"""

from playwright.sync_api import Page, expect
from .base_page import BasePage


class LoginPage(BasePage):
    # Selectors
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    SIGN_IN_BUTTON = "#signin_button"

    # Post-login indicator — the console nav header is always present after login
    CONSOLE_HOME_INDICATOR = "[data-testid='awsc-nav-header']"

    def __init__(self, page: Page, sign_in_url: str):
        super().__init__(page)
        self.sign_in_url = sign_in_url

    def navigate(self) -> None:
        """Open the IAM console sign-in URL."""
        self.navigate_to(self.sign_in_url)

    def login(self, username: str, password: str) -> None:
        """Fill credentials and submit the sign-in form."""
        self.page.locator(self.USERNAME_INPUT).wait_for(state="visible", timeout=15_000)
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.PASSWORD_INPUT, password)
        self.click(self.SIGN_IN_BUTTON)
        # After login the console redirects — dismiss any cookie modal
        self.page.wait_for_load_state("domcontentloaded")
        self.dismiss_cookie_modal()

    def assert_logged_in(self) -> None:
        """Assert that we have reached the AWS Management Console."""
        expect(
            self.page.locator(self.CONSOLE_HOME_INDICATOR)
        ).to_be_visible(timeout=30_000)
