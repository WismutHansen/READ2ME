import asyncio
import logging
import re
import tempfile
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import fitz
import requests
import tldextract
import trafilatura
import wikipedia
from bs4 import BeautifulSoup, Tag
from docling.document_converter import DocumentConverter
from langdetect import LangDetectException, detect
from playwright.async_api import async_playwright
from readabilipy import simple_json_from_html_string

from database.crud import ArticleData, create_article, update_article
from llm.LLM_calls import tldr


# Format in this format: January 1st 2024
def get_formatted_date():
    now = datetime.now()
    day = now.day
    month = now.strftime("%B")
    year = now.year
    suffix = (
        "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    )
    return f"{month} {day}{suffix}, {year}"


# Function to check if word count is less than 200
def check_word_count(text):
    words = re.findall(r"\b\w+\b", text)
    return len(words) < 200


# Function to check for paywall or robot disclaimer
def is_paywall_or_robot_text(text):
    paywall_phrases = [
        "Please make sure your browser supports JavaScript and cookies",
        "To continue, please click the box below",
        "Please enable cookies on your web browser",
        "For inquiries related to this message",
        "If you are a robot",
        "robot.txt",
    ]
    for phrase in paywall_phrases:
        if phrase in text:
            return True
    return False


# Async Function to extract text using playwright
async def extract_with_playwright(url):
    async with async_playwright() as p:
        # Launch a headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Go to the website
            await page.goto(url)

            # Wait for the page to load completely
            await page.wait_for_timeout(2000)  # Increased timeout for loading
            content = await page.content()

        except Exception as e:
            logging.error(f"Error extracting text with Playwright: {e}")
            content = None
        finally:
            await browser.close()

        return content


# Function to extract text using Jina
def extract_with_jina(url):
    try:
        headers = {"X-Return-Format": "html"}
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers)
        if response.status_code == 200:
            if is_paywall_or_robot_text(response.text):
                logging.error(
                    f"Jina could not bypass the paywall: {response.status_code}"
                )
                return None
            else:
                return response.text
        else:
            logging.error(
                f"Jina extraction failed with status code: {response.status_code}"
            )
            return None
    except Exception as e:
        logging.error(f"Error extracting text with Jina: {e}")
        return None


def clean_text(text):
    # Remove extraneous whitespace within paragraphs
    text = re.sub(r"[ \t]+", " ", text)

    # Ensure that there are two newlines between paragraphs
    text = re.sub(r"\n\s*\n", "\n\n", text)  # Ensure two newlines between paragraphs
    text = re.sub(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|\n)\n", "\n\n", text)
    text = re.sub(r"\n[\-_]\n", "", text)  # Remove 3 or more consecutive dashes
    text = re.sub(r"[\-_]{3,}", "", text)  # Remove 3 or more consecutive underscores

    # Convert HTML entities to plain text
    text = BeautifulSoup(text, "html.parser").text

    return text


def clean_wikipedia_content(content):
    # Function to replace headline markers with formatted text
    def replace_headline(match):
        level = len(match.group(1))  # Count the number of '=' symbols
        text = match.group(2).strip()

        # Create appropriate formatting based on the headline level
        if level == 2:
            return f"{text.upper()}\n"
        elif level == 3:
            return f"{text.upper()}\n"
        else:
            return f"{text.upper()}\n"

    # Replace all levels of headlines
    cleaned_content = re.sub(r"(={2,})\s*(.*?)\s*\1", replace_headline, content)

    # Remove any remaining single '=' characters at the start of lines
    cleaned_content = re.sub(r"^\s*=\s*", "", cleaned_content, flags=re.MULTILINE)

    return cleaned_content


def clean_pdf_text(text):
    # Import the re module
    import re

    # Remove headers and footers (assuming they're separated by multiple dashes)
    text = re.sub(r"^.*?-{3,}|-{3,}.*?$", "", text, flags=re.MULTILINE)

    # Remove extraneous whitespace within paragraphs
    text = re.sub(r"[ \t]+", " ", text)

    # Ensure that there are two newlines between paragraphs
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove the references section
    text = re.sub(r"References\s*\n(.*\n)*", "", text, flags=re.IGNORECASE)

    # Remove any remaining citation numbers in square brackets
    text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", text)

    # Remove any remaining URLs
    text = re.sub(r"http[s]?://\S+", "", text)

    # Remove any remaining publication date lines
    text = re.sub(
        r", Vol\. \d+, No\. \d+, Article \d+\. Publication date: [A-Za-z]+ \d{4}\.?",
        "",
        text,
    )

    # Remove any remaining page numbers and headers/footers
    text = re.sub(r"^\d+(\s*[A-Za-z\s,]+)*$", "", text, flags=re.MULTILINE)

    # Remove empty lines at the beginning and end of the text
    text = text.strip()

    # Merge hyphenated words split across lines
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Ensure proper spacing after punctuation
    text = re.sub(r"([.!?])(\w)", r"\1 \2", text)

    # Normalize spaces around em dashes
    text = re.sub(r"\s*—\s*", " — ", text)

    # Format paragraphs: remove single newlines within paragraphs, ensure double newlines between paragraphs
    paragraphs = text.split("\n\n")
    formatted_paragraphs = [
        re.sub(r"\s+", " ", p.strip()) for p in paragraphs if p.strip()
    ]
    text = "\n\n".join(formatted_paragraphs)

    # Remove occurrences with more than three dots
    text = re.sub(r"\.{3,}", "", text)

    # Remove words ending with a hyphen directly before a newline
    text = re.sub(r"(\w+)-\n", r"\1", text)

    # Remove lines that contain numbers only
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)

    return text


def extract_from_wikipedia(url):
    try:
        # Reformat the URL to remove additional parameters
        parsed_url = urlparse(url)
        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        # Extract the title from the URL
        title = clean_url.split("/wiki/")[-1].replace("_", " ")

        # Fetch the Wikipedia page
        page = wikipedia.page(title, auto_suggest=False)

        # Construct the article content
        article_content = f"{page.title}.\n\n"
        article_content += f"From Wikipedia. Retrieved on {get_formatted_date()}\n\n"

        # Add summary
        # article_content += "Summary:\n"
        # article_content += page.summary + "\n\n"

        # Add full content
        article_content += clean_wikipedia_content(page.content)

        return article_content, page.title
    except wikipedia.exceptions.DisambiguationError as e:
        logging.error(f"DisambiguationError: {e}")
        return None, None
    except wikipedia.exceptions.PageError as e:
        logging.error(f"PageError: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Error extracting text from Wikipedia: {e}")
        return None, None


def download_pdf_file(url, timeout=30):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            logging.info(f"PDF file downloaded to {temp_file.name}")
            return temp_file.name
    except requests.RequestException as e:
        logging.error(f"Error downloading PDF: {e}")
        return None


def extract_text_from_pdf(url, article_id: Optional[str] = None):
    try:
        pdf_path = download_pdf_file(url)
        if pdf_path is None:
            logging.error("Failed to download PDF file.")
            return None, None

        # Open the PDF file
        document = fitz.open(pdf_path)

        # Extract the title from the PDF metadata if available
        title = document.metadata.get("title", "No Title Available")

        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        text = result.document.export_to_markdown()
        markdown = result.document.export_to_text()
        tl_dr = tldr(text)
        # Initialize language variable
        language = "Unknown"

        try:
            language = detect(text)
        except LangDetectException:
            language = "Unknown"
        logging.info(f"Detected language: {language}")
        ## Initialize an empty string to store the main text
        # main_text = ""

        ## Loop through each page and extract text
        # for page in document:
        #    main_text += page.get_text()

        document.close()  # Close the document to free resources
        # Set the article in the global state
        new_article = ArticleData(
            title=title,
            language=language,
            plain_text=text,
            md_file=markdown,
            tl_dr=tl_dr,
        )
        if article_id:
            try:
                # Retrieve the article and check if it's not None before passing to create_article
                update_article(article_id, new_article)
            except Exception as e:
                logging.error(f"Couldn't add article data to database: {e}")
            logging.info(f"Extracted text from PDF: {len(text)} characters")
        return text, title

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        return None, None


# This Function extracts the main text from a given URL along with the title,
# list of authors and the date of publication (if available) and formats the text
# accordingly
async def extract_text(url, article_id: Optional[str] = None):
    try:
        try:
            response = requests.head(url, allow_redirects=True)
            resolved_url = response.url
            content_type = response.headers.get("Content-Type", "").lower()
            logging.info("Using extract_text")
            logging.info(f"Resolved URL {resolved_url}")

        except requests.RequestException as e:
            logging.error(f"Error resolving url: {e}")
            return None, None

        if url.lower().endswith(".pdf") or content_type == "application/pdf":
            logging.info(f"Extracting text from PDF: {resolved_url}")
            return extract_text_from_pdf(resolved_url, article_id)

        # Check if it's a Wikipedia URL
        elif "wikipedia.org" in resolved_url:
            logging.info(f"Extracting text from Wikipedia: {resolved_url}")
            return extract_from_wikipedia(resolved_url)

        downloaded = trafilatura.fetch_url(resolved_url)
        if (
            downloaded is None
            or check_word_count(downloaded)
            or is_paywall_or_robot_text(downloaded)
        ):
            logging.info("Extraction with trafilatura failed, trying with playwright")
            # If trafilatura fails extracting html, we try with playwright
            try:
                downloaded = await extract_with_playwright(resolved_url)
                if downloaded is None or is_paywall_or_robot_text(downloaded):
                    logging.info(
                        "Extracted text is a paywall or robot disclaimer, trying with Jina."
                    )
                    downloaded = extract_with_jina(resolved_url)
                    if downloaded is None:
                        return None, None
            except Exception as e:
                logging.error(f"Error extracting text with playwright: {e}")
                return None, None

        if downloaded is None:
            logging.error(f"No content downloaded from {resolved_url}")
            return None, None

        # We use tldextract to extract the main domain name from a URL
        domainname = tldextract.extract(resolved_url)
        main_domain = f"{domainname.domain}.{domainname.suffix}"

        # We use trafilatura to extract the text content from the HTML page
        result = trafilatura.extract(downloaded, include_comments=False)
        # if result is None or check_word_count(result):
        #     logging.error(f"Extracted text is less than 100 words.")
        #     return None, None

        soup = BeautifulSoup(downloaded, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.text if title_tag else ""
        date_tag = soup.find("meta", attrs={"property": "article:published_time"})
        timestamp = date_tag.get("content", "") if isinstance(date_tag, Tag) else ""
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
            # If timestamp is a list, iterate over each item; otherwise, wrap it in a list for uniform processing.
            timestamps = [timestamp] if isinstance(timestamp, str) else timestamp
            for ts in timestamps:
                for date_format in date_formats:
                    try:
                        date = datetime.strptime(ts, date_format)
                        date_str = date.strftime("%B %d, %Y")
                        break
                    except ValueError:
                        continue
                if date_str:
                    break
        if date_str:
            article_content += f"Published on: {date_str}.\n\n"

        # Initialize language variable
        language = "Unknown"

        if result:
            cleaned_text = clean_text(result)
            # Detect language of the content
            try:
                language = detect(cleaned_text)
            except LangDetectException:
                language = "Unknown"
            logging.info(f"Detected language: {language}")
            article_content += cleaned_text

        tl_dr = tldr(article_content)

        # Update article entry in database with new entry fields
        if article_id:
            try:
                new_article = ArticleData(
                    title=title,
                    date_published=date_str if date_str else "",
                    language=language,
                    plain_text=article_content,
                    tl_dr=tl_dr,
                )
                update_article(article_id, new_article)
                logging.info(f"article {article_id} sucessfully updated")
            except Exception as e:
                logging.error(f"Couldn't add article data to database: {e}")

        return article_content, title, tl_dr

    except Exception as e:
        logging.error(f"Error extracting text from HTML: {e}")
        return None, None, None


def readability(url):
    response = requests.head(url, allow_redirects=True)
    resolved_url = response.url
    downloaded = trafilatura.fetch_url(resolved_url)
    article = simple_json_from_html_string(downloaded, use_readability=True)

    title = article.get("title", "No Title")
    byline = article.get("byline")
    content = article.get("plain_text", [])

    markdown = f"# {title}\n\n"
    if byline:
        markdown += f"**Written by:** {byline}\n\n"
    markdown += f"**From:** {url}\n\n"

    # Check if content is iterable and then process it
    if isinstance(content, list):
        markdown += "\n".join(
            [
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ]
        )

    return markdown


if __name__ == "__main__":
    url = input("Enter URL to extract text from: ")
    article_content, title = asyncio.run(extract_text(url))
    if article_content:
        print(article_content)
    else:
        print("Failed to extract text.")
