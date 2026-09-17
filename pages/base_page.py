"""
pages/base_page.py
Shared helpers used by every page object.
"""

from playwright.sync_api import Page, expect


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def navigate_to(self, url: str) -> None:
        """
        Hard-navigate to an absolute URL.

        Uses 'domcontentloaded' instead of 'networkidle' because AWS console
        pages maintain persistent SSE / long-polling connections that prevent
        'networkidle' from ever firing, causing navigation to time out.
        """
        self.page.goto(url, wait_until="domcontentloaded")
        self.dismiss_cookie_modal()

    def dismiss_cookie_modal(self) -> None:
        """
        Dismiss the AWS cookie-consent modal if it appears.
        AWS shows this on first visit and after cross-domain navigation.
        We click 'Decline' to avoid changing cookie state; either button
        dismisses the overlay so the page underneath becomes interactive.
        """
        try:
            decline_btn = self.page.get_by_role("button", name="Decline")
            decline_btn.wait_for(state="visible", timeout=3_000)
            decline_btn.click()
        except Exception:
            pass  # modal not present — safe to proceed

    # ------------------------------------------------------------------
    # Element interaction helpers
    # ------------------------------------------------------------------
    def fill(self, selector: str, value: str) -> None:
        self.page.locator(selector).fill(value)

    def click(self, selector: str) -> None:
        self.page.locator(selector).click()

    def get_text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text()

    # ------------------------------------------------------------------
    # Wait helpers
    # ------------------------------------------------------------------
    def wait_for_text(self, text: str, timeout: int = 30_000) -> None:
        """Wait until the given text is visible anywhere on the page."""
        self.page.get_by_text(text, exact=False).first.wait_for(
            state="visible", timeout=timeout
        )

    def wait_for_url_contains(self, fragment: str, timeout: int = 30_000) -> None:
        self.page.wait_for_url(f"**{fragment}**", timeout=timeout)

    def reload(self) -> None:
        self.page.reload(wait_until="domcontentloaded")
        self.dismiss_cookie_modal()
