import newspaper
import os
import re
from dotenv import load_dotenv
import aiofiles
import asyncio
import logging
import aiohttp


async def fetch_articles():
    from .task_file_handler import add_task

    load_dotenv()
    sources_file = os.getenv("SOURCES_FILE")
    keywords_file = os.getenv("KEYWORDS_FILE")

    # Function to create sources.txt
    async def create_sources_file(file_path, urls):
        try:
            async with aiofiles.open(file_path, "w") as file:
                for url in urls:
                    await file.write(url + "\n")
            print(f"Created {file_path} with {len(urls)} URLs.")
        except Exception as e:
            print(f"Error creating {file_path}: {e}")

    # Function to create keywords.txt
    async def create_keywords_file(file_path, keywords):
        try:
            async with aiofiles.open(file_path, "w") as file:
                for keyword in keywords:
                    await file.write(keyword + "\n")
            print(f"Created {file_path} with {len(keywords)} keywords.")
        except Exception as e:
            print(f"Error creating {file_path}: {e}")

    # Create sample sources.txt and keywords.txt if they don't exist
    sample_sources = ["https://example.com"]
    sample_keywords = ["example", "test"]
    if not os.path.exists(sources_file):
        await create_sources_file(sources_file, sample_sources)
    if not os.path.exists(keywords_file):
        await create_keywords_file(keywords_file, sample_keywords)

    # Function to read URLs from a file
    async def read_urls_from_file(file_path):
        try:
            async with aiofiles.open(file_path, "r") as file:
                urls = [line.strip() for line in await file.readlines() if line.strip()]
                print(f"Read {len(urls)} URLs from {file_path}")
                return urls
        except Exception as e:
            print(f"Error reading URLs from file: {e}")
            return []

    # Function to read keywords from a file
    async def read_keywords_from_file(file_path):
        try:
            async with aiofiles.open(file_path, "r") as file:
                keywords = [
                    line.strip().lower()
                    for line in await file.readlines()
                    if line.strip()
                ]
                print(f"Read {len(keywords)} keywords from {file_path}")
                return keywords
        except Exception as e:
            print(f"Error reading keywords from file: {e}")
            return []

    # Read URLs and keywords from files
    if not sources_file:
        print("SOURCES_FILE environment variable not set.")
    else:
        source_urls = await read_urls_from_file(sources_file)

    if not keywords_file:
        print("KEYWORDS_FILE environment variable not set.")
    else:
        keywords = await read_keywords_from_file(keywords_file)

    # Compile regular expressions for keywords, ensuring whole word matches
    keyword_patterns = [
        re.compile(r"\b" + re.escape(keyword).replace("\\ ", "\\s+") + r"\b")
        for keyword in keywords
    ]

    # Debugging: print the regex patterns
    print("Compiled regex patterns:")
    for pattern in keyword_patterns:
        print(pattern.pattern)

    async def process_article(article_url, patterns):
        try:
            # Check if any keyword pattern is present in the article URL
            modified_article_url = article_url.replace("-", " ").lower()
            for pattern in patterns:
                if pattern.search(modified_article_url):
                    logging.info(
                        f"Keyword '{pattern.pattern}' found in URL: {article_url}"
                    )
                    await add_task("url", article_url, "edge_tts")
                    return

            logging.debug(f"No keywords found in URL: {article_url}")

        except Exception as e:
            logging.error(f"Failed to process article {article_url}: {e}")

    async def process_source(source_url, patterns):
        paper = newspaper.build(source_url, memoize_articles=True)
        logging.info(f"Found {len(paper.articles)} articles in {source_url}")

        tasks = []
        for article in paper.articles:
            tasks.append(process_article(article.url, patterns))

        await asyncio.gather(*tasks)

    if sources_file and keywords_file:
        await asyncio.gather(
            *[process_source(url, keyword_patterns) for url in source_urls]
        )

    # Debugging: Show completion message
    print("Completed processing all sources and articles.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_articles())
