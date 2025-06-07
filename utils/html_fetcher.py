#!/usr/bin/env python
# -----------------------------------------------------------
# html_fetcher.py
#
#  * Library use:
#        import asyncio
#        from html_fetcher import fetch_html
#
#        html = asyncio.run(fetch_html("https://example.com"))
#
#  * CLI use:
#        uv pip install playwright         # install deps
#        playwright install chromium       # one-time browser download
#        python html_fetcher.py https://example.com --out page.html
#
# -----------------------------------------------------------
import argparse
import asyncio
from pathlib import Path
from typing import Optional
import trafilatura
from utils.paywall_detector import is_paywall_or_robot_text
from playwright.async_api import async_playwright

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-infobars",
    "--disable-blink-features=AutomationControlled",
]


async def fetch_html(
    url: str,
    *,
    html_path: str | Path | None = None,
    headless: bool = True,
    wait_seconds: float = 0,
    user_agent: Optional[str] = None,
) -> str:
    """
    Retrieve the serialised DOM HTML for *url* with Playwright.

    Parameters
    ----------
    url : str
        Target URL.
    html_path : str | Path | None, optional
        If given, write the HTML to this file.
    headless : bool, optional
        Headless Chromium? Default True.
    wait_seconds : float, optional
        Seconds to await after navigation (for JS-heavy pages).
    user_agent : str | None, optional
        Override the UA string if needed.

    Returns
    -------
    str
        The HTML string.
    """
    ua = (
        user_agent
        or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=ua,
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )

        page = await context.new_page()
        await page.goto(url, wait_until="load")
        if wait_seconds:
            await asyncio.sleep(wait_seconds)

        html = await page.content()

        if html_path:
            Path(html_path).write_text(html, encoding="utf-8")

        await browser.close()

    return html


def extract_content(html: str) -> str | None:
    return trafilatura.extract(html, include_comments=False)


# ────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch rendered HTML for a URL via Playwright."
    )
    parser.add_argument("url", help="Target URL.")
    parser.add_argument(
        "-o",
        "--out",
        help="File to save HTML (optional).",
        default=None,
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=0,
        metavar="SECONDS",
        help="Extra wait time after load (JS-heavy pages).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Run browser headful instead of headless.",
    )
    return parser.parse_args()


async def _run_cli() -> None:
    args = _parse_args()
    html = await fetch_html(
        args.url,
        html_path=args.out,
        headless=not args.show,
        wait_seconds=args.wait,
    )
    content = extract_content(html)
    if not args.out:
        print(content)
        print("\n----------------------\n")
        print(is_paywall_or_robot_text(content))


if __name__ == "__main__":
    asyncio.run(_run_cli())
