from playwright.sync_api import sync_playwright

import datetime
import logging
import cloudscraper
from bs4 import BeautifulSoup
import trafilatura
import tldextract
import re


def scrape_main_text(url):
    with sync_playwright() as p:
        # Launch a headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to the website
        page.goto(url)

        # Wait for the page to load completely
        page.wait_for_timeout(2000)  # Adjust the timeout as needed

        # Extract the main text content
        content = page.content()
        browser.close()

    return content, url


def extract_text(content, url):
    domainname = tldextract.extract(url)
    main_domain = f"{domainname.domain}.{domainname.suffix}"
    result = trafilatura.extract(content, include_comments=False)
    soup = BeautifulSoup(content, "html.parser")
    title = soup.find("title").text if soup.find("title") else ""
    date_tag = soup.find("meta", attrs={"property": "article:published_time"})
    timestamp = date_tag["content"] if date_tag else ""
    article_content = f"{title}.\n\n" if title else ""
    article_content += f"From {main_domain}.\n\n"
    authors = []
    for attr in ["name", "property"]:
        author_tags = soup.find_all("meta", attrs={attr: "author"})
        for tag in author_tags:
            if tag and tag.get("content"):
                authors.append(tag["content"])
    authors = sorted(set(authors))
    if authors:
        article_content += "Written by: " + ", ".join(authors) + ".\n\n"
    date_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
    ]
    date_str = ""
    if timestamp:
        for date_format in date_formats:
            try:
                date = datetime.datetime.strptime(timestamp, date_format)
                date_str = date.strftime("%B %d, %Y")
                break
            except ValueError:
                continue
    if date_str:
        article_content += f"Published on: {date_str}.\n\n"
    if result:
        lines = result.split("\n")
        filtered_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if len(line.split()) < 15:
                if i + 1 < len(lines) and len(lines[i + 1].split()) < 15:
                    while i < len(lines) and len(lines[i].split()) < 15:
                        i += 1
                    continue
            filtered_lines.append(line)
            i += 1
        formatted_text = "\n\n".join(filtered_lines)
        formatted_text = re.sub(r"\n[\-_]\n", "\n\n", formatted_text)
        formatted_text = re.sub(r"[\-_]{3,}", "", formatted_text)
        article_content += formatted_text
    return article_content, title


if __name__ == "__main__":
    content, url = scrape_main_text(input("Enter URL to extract text from: "))
    article_content, title = extract_text(content, url)
    print(article_content)
