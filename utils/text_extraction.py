import datetime
import logging
import requests
from bs4 import BeautifulSoup
import trafilatura
import tldextract
import re

# Function to check if word count is less than 400
def check_word_count(text):
    return len(text.split()) < 400

# Function to check for paywall or robot disclaimer
def is_paywall_or_robot_text(text):
    paywall_phrases = [
        "Please make sure your browser supports JavaScript and cookies",
        "To continue, please click the box below",
        "Please enable cookies on your web browser",
        "For inquiries related to this message",
        "If you are a robot"
    ]
    for phrase in paywall_phrases:
        if phrase in text:
            return True
    return False

# This Function extracts the main text from a given URL along with the title,
# list of authors and the date of publication (if available) and formats the text
# accordingly
def extract_text(url):
    try:    
        try:
            response = requests.head(url, allow_redirects=True)
            resolved_url = response.url
            print(f"Resolved URL {resolved_url}")
        except requests.RequestException as e:
            logging.error(f"Error resolving url: {e}")
            return None, None

        downloaded = trafilatura.fetch_url(url)
        if downloaded is None or check_word_count(downloaded) or is_paywall_or_robot_text(downloaded):
            print("Extraction with trafilatura failed, trying with playwright")
            # If trafilatura fails extracting html, we try with playwright
            try:
                downloaded = extract_with_playwright(resolved_url)
                if is_paywall_or_robot_text(downloaded):
                    print("Extracted text is a paywall or robot disclaimer.")
                    return None, None
            except Exception as e:   
                logging.error(f"Error extracting text with playwright: {e}")
                return None, None
            
        # We use tldextract to extract the main domain name from a URL
        domainname = tldextract.extract(resolved_url)
        main_domain = f"{domainname.domain}.{domainname.suffix}"
        
        # We use trafilatura to extract the text content from the HTML page
        result = trafilatura.extract(downloaded, include_comments=False)
        soup = BeautifulSoup(downloaded, "html.parser")
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
            I = 0
            while I < len(lines):
                line = lines[I]
                if len(line.split()) < 15:
                    if I + 1 < len(lines) and len(lines[I + 1].split()) < 15:
                        while I < len(lines) and len(lines[I].split()) < 15:
                            I += 1
                        continue
                filtered_lines.append(line)
                I += 1
            formatted_text = "\n\n".join(filtered_lines)
            formatted_text = re.sub(r"\n[\-_]\n", "\n\n", formatted_text)
            formatted_text = re.sub(r"[\-_]{3,}", "", formatted_text)
            article_content += formatted_text
        return article_content, title
    except Exception as e:
        logging.error(f"Error extracting text from HTML: {e}")
        return None, None
    
def extract_with_playwright(url):
    from playwright.sync_api import sync_playwright
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
        return content

if __name__ == "__main__":
    article_content, title = extract_text(input("Enter URL to extract text from: "))
    if article_content:
        print(article_content)
    else:
        print("Failed to extract text.")