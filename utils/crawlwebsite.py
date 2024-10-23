from urllib.parse import urljoin, urlparse, urldefrag
import aiohttp
from bs4 import BeautifulSoup
from utils.text_extraction import extract_text
import logging
import asyncio

logging.basicConfig(level=logging.INFO)


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def crawl_website(root_url, max_pages=100):
    parsed_root = urlparse(root_url)
    base_url = f"{parsed_root.scheme}://{parsed_root.netloc}"

    visited = set()
    to_visit = {root_url}
    extracted_content = []

    async with aiohttp.ClientSession() as session:
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop()
            url_without_fragment = urldefrag(url)[0]

            if url_without_fragment in visited:
                continue

            logging.info(f"Crawling: {url}")
            visited.add(url_without_fragment)

            try:
                html = await fetch(session, url)
                soup = BeautifulSoup(html, "html.parser")

                # Extract text content
                content, title = await extract_text(url)
                if content:
                    extracted_content.append((title, url, content))

                # Find new links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(base_url, href)
                    full_url_without_fragment = urldefrag(full_url)[0]
                    if (
                        full_url.startswith(base_url)
                        and full_url_without_fragment not in visited
                    ):
                        to_visit.add(full_url)

            except Exception as e:
                logging.error(f"Error processing {url}: {e}")

    return extracted_content


def save_to_markdown(content, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for title, url, text in content:
            f.write(f"# {title}\n\n")
            f.write(f"Source: {url}\n\n")
            f.write(f"{text}\n\n")
            f.write("---\n\n")  # Separator between pages


async def main():
    root_url = input("Enter the root URL to crawl: ")
    output_file = input("Enter the output file name (e.g., output.md): ")
    max_pages = int(input("Enter the maximum number of pages to crawl: "))

    extracted_content = await crawl_website(root_url, max_pages)
    save_to_markdown(extracted_content, output_file)
    logging.info(f"Crawling completed. Content saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

