import json
import os
import re
import aiofiles
import asyncio
import logging
import newspaper
from .task_file_handler import add_task

MAX_ARTICLES_PER_SOURCE = 10

async def fetch_articles():

    sources_file = "sources.json"

    async def read_sources_from_json(file_path):
        try:
            async with aiofiles.open(file_path, "r") as file:
                data = json.loads(await file.read())
                print(f"Read configuration from {file_path}")
                return data
        except Exception as e:
            print(f"Error reading configuration from file: {e}")
            return {"global_keywords": [], "sources": []}

    async def create_sample_sources_file(file_path):
        sample_data = {
            "global_keywords": ["example", "test"],
            "sources": [
                {
                    "url": "https://example.com",
                    "keywords": ["specific", "example"]
                },
                {
                    "url": "https://all-articles-example.com",
                    "keywords": ["*"]
                }
            ]
        }
        try:
            async with aiofiles.open(file_path, "w") as file:
                await file.write(json.dumps(sample_data, indent=2))
            print(f"Created sample {file_path}")
        except Exception as e:
            print(f"Error creating sample {file_path}: {e}")

    if not os.path.exists(sources_file):
        await create_sample_sources_file(sources_file)

    config = await read_sources_from_json(sources_file)
    global_keywords = config.get("global_keywords", [])
    sources = config.get("sources", [])

    def compile_patterns(keywords):
        return [re.compile(r"\b" + re.escape(keyword).replace("\\ ", "\\s+") + r"\b", re.IGNORECASE) for keyword in keywords if keyword != "*"]

    global_patterns = compile_patterns(global_keywords)

    async def process_article(article_url, global_patterns, source_patterns, download_all):
        try:
            if download_all:
                logging.info(f"Adding article to task list: {article_url}")
                await add_task("url", article_url, "edge_tts")
                return True

            modified_article_url = article_url.replace("-", " ").lower()
            all_patterns = global_patterns + source_patterns
            
            for pattern in all_patterns:
                if pattern.search(modified_article_url):
                    logging.info(f"Keyword '{pattern.pattern}' found in URL: {article_url}")
                    await add_task("url", article_url, "edge_tts")
                    return True

            logging.debug(f"No keywords found in URL: {article_url}")
            return False

        except Exception as e:
            logging.error(f"Failed to process article {article_url}: {e}")
            return False

    async def process_source(source):
        source_url = source["url"]
        source_keywords = source.get("keywords", [])
        download_all = "*" in source_keywords
        source_patterns = compile_patterns(source_keywords)

        paper = newspaper.build(source_url, memoize_articles=True)
        logging.info(f"Found {len(paper.articles)} articles in {source_url}")

        tasks = []
        articles_processed = 0
        for article in paper.articles:
            if download_all and articles_processed >= MAX_ARTICLES_PER_SOURCE:
                break
            task = asyncio.create_task(process_article(article.url, global_patterns, source_patterns, download_all))
            tasks.append(task)
            if download_all:
                articles_processed += 1

        results = await asyncio.gather(*tasks)
        articles_added = sum(results)
        logging.info(f"Added {articles_added} articles from {source_url}")

    await asyncio.gather(*[process_source(source) for source in sources])

    print("Completed processing all sources and articles.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_articles())