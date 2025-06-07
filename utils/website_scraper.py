#!/usr/bin/env python3
"""
website_scraper.py
=========================

Asynchronously fetch **raw HTML** with Playwright:

• random User-Agent pool
• retries with exponential back-off
• pluggable browser (Chromium / Firefox / WebKit)
• proxy support
• navigation & overall timeouts
• optional selector wait (for “rendered” SPAs)
• structured logging

Install deps (Playwright + browser binaries):
    uv pip install playwright
    playwright install

Example
-------
import asyncio
from robust_playwright_fetch import get_html

html = asyncio.run(
    get_html(
        "https://example.com",
        selector="main",          # wait until <main> is in the DOM
        retries=2,
        timeout=45,
        proxy="socks5://127.0.0.1:9050",
    )
)
print(html[:500])
"""

import asyncio
import logging
import random
import sys
import time
from typing import Optional
import trafilatura

from playwright.async_api import (
    async_playwright,
    BrowserType,
    TimeoutError as PWTimeout,
)

# ─────────────────────────────── Config ─────────────────────────────── #

USER_AGENTS = [
    # Chromium, Safari, Firefox
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
    ),
]

logger = logging.getLogger("robust_playwright_fetch")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)

# ──────────────────────────── Core Function ─────────────────────────── #


async def get_html(
    url: str,
    *,
    browser_name: str = "chromium",  # or "firefox", "webkit"
    headless: bool = True,
    selector: Optional[str] = None,  # CSS selector to await; None = networkidle
    timeout: int = 30,  # seconds for *overall* op
    nav_timeout: int = 20,  # seconds for page.goto()
    retries: int = 3,  # total attempts
    backoff: float = 1.5,  # exponential back-off factor
    proxy: Optional[str] = None,  # e.g. "http://user:pass@1.2.3.4:3128"
    extra_headers: Optional[dict] = None,
) -> str:
    """
    Fetch raw HTML with Playwright and return it as a string.

    Raises
    ------
    RuntimeError
        If all retries fail.
    """
    start = time.perf_counter()
    last_exc: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            return await _single_attempt(
                url,
                browser_name,
                headless,
                selector,
                nav_timeout,
                proxy,
                extra_headers,
            )
        except Exception as exc:  # broad: want to retry on *anything*
            last_exc = exc
            logger.warning(f"Attempt {attempt}/{retries} failed for {url}: {exc!r}")
            if attempt < retries:
                sleep_time = backoff**attempt
                logger.info(f"Retrying in {sleep_time:.1f}s…")
                await asyncio.sleep(sleep_time)

    duration = time.perf_counter() - start
    raise RuntimeError(
        f"Failed to fetch {url} after {retries} attempts "
        f"({duration:.2f}s). Last error: {last_exc}"
    )


# ─────────────────────────── Helper Routine ─────────────────────────── #


async def _single_attempt(
    url: str,
    browser_name: str,
    headless: bool,
    selector: Optional[str],
    nav_timeout: int,
    proxy: Optional[str],
    extra_headers: Optional[dict],
) -> str:
    ua = random.choice(USER_AGENTS)

    launch_kwargs = {"headless": headless}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}

    async with async_playwright() as p:
        browser_type: BrowserType = getattr(p, browser_name)
        browser = await browser_type.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=ua, extra_http_headers=extra_headers or {}
        )
        page = await context.new_page()

        try:
            logger.debug(f"Navigating to {url} with UA={ua}")
            await page.goto(
                url, wait_until="domcontentloaded", timeout=nav_timeout * 1000
            )

            if selector:
                logger.debug(f"Waiting for selector {selector!r}")
                await page.wait_for_selector(selector, timeout=nav_timeout * 1000)
            else:
                # Wait for network to be quiet *and* a bit of JS flushing
                await page.wait_for_load_state(
                    "networkidle", timeout=nav_timeout * 1000
                )
                await page.wait_for_timeout(500)  # tiny buffer for late JS

            html = await page.content()
            if not html or len(html) < 100:
                raise RuntimeError("Empty or very small HTML received")

            return html

        except PWTimeout as te:
            raise RuntimeError(f"Timeout: {te}") from te
        finally:
            await browser.close()


def extract_content(html: str) -> str | None:
    return trafilatura.extract(html, include_comments=False)


# ────────────────────────────── CLI Hook ────────────────────────────── #

if __name__ == "__main__":
    # quick CLI for ad-hoc testing: python robust_playwright_fetch.py https://example.com
    import argparse

    parser = argparse.ArgumentParser(description="Fetch HTML via Playwright.")
    parser.add_argument("url")
    parser.add_argument("-s", "--selector", help="CSS selector to wait for")
    parser.add_argument(
        "-t", "--timeout", type=int, default=30, help="overall timeout (s)"
    )
    parser.add_argument("-r", "--retries", type=int, default=3, help="retry attempts")
    parser.add_argument(
        "-b", "--browser", default="chromium", choices=["chromium", "firefox", "webkit"]
    )
    parser.add_argument("--proxy", help="proxy URL, e.g. http://user:pass@host:port")
    args = parser.parse_args()

    try:
        html_output = asyncio.run(
            get_html(
                args.url,
                selector=args.selector,
                timeout=args.timeout,
                retries=args.retries,
                browser_name=args.browser,
                proxy=args.proxy,
            )
        )
        content = extract_content(html_output)
        print(content)
    except Exception as err:
        logger.error(err)
        sys.exit(1)
