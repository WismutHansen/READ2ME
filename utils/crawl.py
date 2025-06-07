#!/usr/bin/env python3
"""
crawl.py – asynchronous utility to fetch the raw HTML of ONE page.

Example
-------
import asyncio
from get_html import get_html

html = asyncio.run(get_html("https://example.com"))
print(html[:500])  # first 500 chars

Dependencies
------------
uv pip install aiohttp
"""

import random
from typing import List, Optional

import aiohttp
from aiohttp import ClientTimeout

# A few mainstream User-Agents for simple rotation
UA_POOL: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.text()  # raw HTML


async def get_html(
    url: str,
    timeout: int = 30,
    user_agents: Optional[List[str]] = None,
) -> str:
    """
    Download and return raw HTML for `url`.
    Parameters
    ----------
    url : str
        Absolute or scheme-less URL; we assume https:// if none given.
    timeout : int, optional
        Total request timeout (seconds).  Default is 30.
    user_agents : list[str] | None, optional
        Override or extend the default UA pool.

    Returns
    -------
    str
        Raw HTML content.
    """
    if "://" not in url:
        url = "https://" + url

    ua_pool = user_agents or UA_POOL
    headers = {"User-Agent": random.choice(ua_pool)}

    async with aiohttp.ClientSession(
        headers=headers, timeout=ClientTimeout(total=timeout)
    ) as session:
        return await _fetch(session, url)


# Optional CLI: python get_html.py https://example.com > page.html
if __name__ == "__main__":  # pragma: no cover
    import argparse, asyncio, sys

    parser = argparse.ArgumentParser(
        description="Fetch raw HTML of a single page and write to stdout."
    )
    parser.add_argument("url", help="URL to fetch (https://example.com)")
    parser.add_argument(
        "-t", "--timeout", type=int, default=30, help="Request timeout in seconds"
    )
    args = parser.parse_args()

    try:
        html_text = asyncio.run(get_html(args.url, timeout=args.timeout))
        sys.stdout.write(html_text)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
