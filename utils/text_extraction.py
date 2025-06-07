#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import tempfile
import time
from datetime import datetime
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse

import fitz
import requests
import tldextract
import trafilatura
import wikipedia
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from requests.adapters import HTTPAdapter, Retry

from database.crud import ArticleData, update_article
from llm.LLM_calls import tldr
from utils.paywall_detector import is_paywall_or_robot_text
from utils.website_scraper import get_html

# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def get_formatted_date() -> str:
    """Return current date in “January 1st 2024” format."""
    now = datetime.now()
    suffix = (
        "th"
        if 11 <= now.day <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(now.day % 10, "th")
    )
    return f"{now.strftime('%B')} {now.day}{suffix}, {now.year}"


def check_word_count(text: str, minimum: int = 100) -> bool:
    """True if text contains fewer than *minimum* words."""
    return len(re.findall(r"\b\w+\b", text)) < minimum


# --------------------------------------------------------------------------- #
# HTTP session with automatic back-off retries
# --------------------------------------------------------------------------- #

_SESSION: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        _SESSION.mount("https://", HTTPAdapter(max_retries=retries))
        _SESSION.mount("http://", HTTPAdapter(max_retries=retries))
    return _SESSION


# --------------------------------------------------------------------------- #
# Fetch strategies – each must implement (url) -> Optional[str]
# --------------------------------------------------------------------------- #


def fetch_via_trafilatura(url: str) -> Optional[str]:
    """Raw HTML via trafilatura (fast)."""
    logging.debug("Trying trafilatura…")
    return trafilatura.fetch_url(url)


async def fetch_via_playwright(url: str) -> Optional[str]:
    """Raw HTML via headless Playwright (best for JS-heavy sites)."""
    logging.debug("Trying Playwright…")
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)  # firefox avoids some blocks
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=20_000)
            await page.wait_for_load_state("networkidle")  # JS finished
            content = await page.content()
            return content
        finally:
            await browser.close()


def fetch_via_jina(url: str) -> Optional[str]:
    """Raw HTML via jina.ai extractor service (last resort)."""
    logging.debug("Trying Jina AI service…")
    r = get_session().get(
        f"https://r.jina.ai/http://{url}", headers={"X-Return-Format": "html"}
    )
    if r.ok:
        return r.text
    logging.error("Jina request failed: %s", r.status_code)
    return None


FETCH_STRATEGIES: List[Callable[[str], "asyncio.Future[str]"]] = [
    fetch_via_trafilatura,
    fetch_via_playwright,
    fetch_via_jina,
]

# --------------------------------------------------------------------------- #
# Clean-up helpers
# --------------------------------------------------------------------------- #


def clean_text(text: str) -> str:
    """Basic whitespace / HTML entity clean-up."""
    text = BeautifulSoup(text, "html.parser").text
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"\n[\-_]{3,}\n", "\n\n", text)
    return text.strip()


def clean_wikipedia_content(content: str) -> str:
    def repl(m):  # headline → ALL-CAPS
        return f"{m.group(2).strip().upper()}\n"

    return re.sub(r"(={2,})\s*(.*?)\s*\1", repl, content)


# --------------------------------------------------------------------------- #
# Wikipedia, PDF and generic extractors
# --------------------------------------------------------------------------- #


def extract_from_wikipedia(url: str) -> Tuple[str, str]:
    title = urlparse(url).path.split("/wiki/")[-1].replace("_", " ")
    page = wikipedia.page(title, auto_suggest=False)
    body = f"{page.title}.\n\nFrom Wikipedia. Retrieved on {get_formatted_date()}\n\n"
    body += clean_wikipedia_content(page.content)
    return body, page.summary


def download_pdf(url: str) -> str:
    r = get_session().get(url, timeout=30)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(r.content)
        return tmp.name


def extract_from_pdf(url: str) -> Tuple[str, str]:
    path = download_pdf(url)
    doc = fitz.open(path)
    title = doc.metadata.get("title", "") or "Untitled PDF"
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text.strip(), title


# --------------------------------------------------------------------------- #
# Master extractor – the public entry-point
# --------------------------------------------------------------------------- #


async def extract_text(
    url: str, article_id: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Try multiple fetch strategies until one succeeds, then parse.
    """
    resolved = get_session().head(url, allow_redirects=True, timeout=15).url
    ctype = get_session().head(resolved, timeout=15).headers.get("Content-Type", "")
    logging.info("Resolved %s", resolved)

    # --- Shortcut: PDFs ---------------------------------------------------- #
    if resolved.lower().endswith(".pdf") or ctype.startswith("application/pdf"):
        logging.info("Treating as PDF")
        body, title = extract_from_pdf(resolved)
        return body, title, tldr(body)

    # --- Shortcut: Wikipedia ---------------------------------------------- #
    if "wikipedia.org/wiki/" in resolved:
        logging.info("Treating as Wikipedia")
        body, summary = extract_from_wikipedia(resolved)
        return body, summary, summary

    # --- HTML fall-through ------------------------------------------------- #
    html: Optional[str] = None
    for strategy in FETCH_STRATEGIES:
        try:
            if asyncio.iscoroutinefunction(strategy):
                html = await strategy(resolved)
            else:
                html = strategy(resolved)
            # Validation
            if not html or check_word_count(html) or is_paywall_or_robot_text(html):
                logging.warning(
                    "Strategy %s produced unusable output", strategy.__name__
                )
                html = None
                continue
            break  # success!
        except Exception as exc:
            logging.error("Strategy %s failed: %s", strategy.__name__, exc)
    if html is None:
        logging.error("All fetch strategies failed.")
        return None, None, None

    # --- Extract article text --------------------------------------------- #
    extracted = trafilatura.extract(html, include_comments=False)
    if not extracted:
        logging.error("Trafilatura extraction failed.")
        return None, None, None
    cleaned = clean_text(extracted)
    if check_word_count(cleaned):
        logging.error("Cleaned article still too short.")
        return None, None, None
    if is_paywall_or_robot_text(cleaned):
        logging.error("Still looks like paywall text.")
        return None, None, None

    # --- Meta information -------------------------------------------------- #
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").split(" | ")[0].strip()
    domain = (
        f"{tldextract.extract(resolved).domain}.{tldextract.extract(resolved).suffix}"
    )
    body = f"{title}.\n\nFrom {domain}.\n\n{cleaned}" if title else cleaned

    summary = tldr(body)
    if article_id:
        update_article(
            article_id,
            ArticleData(
                title=title,
                source=domain,
                plain_text=body,
                tl_dr=summary,
            ),
        )
    return body, title, summary


# --------------------------------------------------------------------------- #
# Script entry-point
# --------------------------------------------------------------------------- #

if __name__ == "__main__":  # pragma: no cover
    # Only configure logging when run as main script
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    target = input("Enter URL to extract text from: ").strip()
    start = time.time()
    out, title, short = asyncio.run(extract_text(target))
    if out:
        print(
            f"\n--- {title or 'Article'} -------------------------------------------\n"
        )
        print(out[:10_000])  # prevent accidental megapastes
        print(
            "\n--- TL;DR -----------------------------------------------------------\n"
        )
        print(short)
    else:
        print("Extraction failed.")
    logging.info("Done in %.2fs", time.time() - start)
