import json
import os
import re
import aiofiles
import asyncio
import logging
import newspaper
from .task_file_handler import add_task
from .rssfeed import find_rss_feed, get_articles_from_feed

MAX_ARTICLES_PER_SOURCE = 10


def compile_patterns(keywords):
    return [
        re.compile(
            r"\b" + re.escape(keyword).replace("\\ ", "\\s+") + r"\b", re.IGNORECASE
        )
        for keyword in keywords
        if keyword != "*"
    ]


async def fetch_articles():
    sources_file = "sources.json"

    async def read_sources_from_json(file_path):
        try:
            async with aiofiles.open(file_path, "r") as file:
                data = json.loads(await file.read())
                logging.info(f"Read configuration from {file_path}")
                return data
        except Exception as e:
            logging.error(f"Error reading configuration from file: {e}")
            return {"global_keywords": [], "sources": []}

    async def create_sample_sources_file(file_path):
        sample_data = {
            "global_keywords": ["example", "test"],
            "sources": [
                {"url": "https://example.com", "keywords": ["specific", "example"]},
                {"url": "https://all-articles-example.com", "keywords": ["*"]},
            ],
        }
        try:
            async with aiofiles.open(file_path, "w") as file:
                await file.write(json.dumps(sample_data, indent=2))
            print(f"Created sample {file_path}")
        except Exception as e:
            print(f"Error creating sample {file_path}: {e}")

    if not os.path.exists(sources_file):
        await create_sample_sources_file(sources_file)

    logging.info("Starting fetch_articles function")
    config = await read_sources_from_json(sources_file)
    global_keywords = config.get("global_keywords", [])
    sources = config.get("sources", [])

    logging.info(f"Global keywords: {global_keywords}")
    logging.info(f"Number of sources: {len(sources)}")

    global_patterns = compile_patterns(global_keywords)
    logging.info(f"Compiled {len(global_patterns)} global patterns")

    for i, source in enumerate(sources, 1):
        logging.info(f"Processing source {i}/{len(sources)}: {source['url']}")
        await process_source(source, global_patterns)
        logging.info(f"Completed processing source {i}/{len(sources)}: {source['url']}")

    logging.info("Completed processing all sources and articles.")


async def process_article(article_url, global_patterns, source_patterns, download_all):
    try:
        if download_all:
            logging.info(f"Adding article to task list: {article_url}")
            await add_task("url", article_url, "edge_tts")
            return True

        # Extract the headline from the URL
        headline = article_url.split("/")[-1].replace("-", " ").lower()
        all_patterns = (
            global_patterns
            if not source_patterns
            else (global_patterns + source_patterns)
        )

        for pattern in all_patterns:
            if pattern.search(headline):
                logging.info(
                    f"Keyword '{pattern.pattern}' found in headline: {article_url}"
                )
                await add_task("url", article_url, "edge_tts")
                return True

        logging.debug(f"No keywords found in headline: {article_url}")
        return False

    except Exception as e:
        logging.error(f"Failed to process article {article_url}: {e}")
        return False


async def process_source(source, global_patterns):
    source_url = source["url"]
    source_keywords = source.get("keywords", [])
    download_all = "*" in source_keywords
    #    filter_quality = "%" in source_keywords # if the % character is used, all articles should first be rated by th score_text function
    source_patterns = compile_patterns([k for k in source_keywords if k and k != "*"])

    if source.get("is_rss", False):
        logging.info(f"Source {source_url} is an RSS feed.")
        articles = get_articles_from_feed(source_url)
    else:
        logging.info(f"Starting to build newspaper for source: {source_url}")
        paper = newspaper.build(source_url, memoize_articles=True)
        logging.info(f"Found {len(paper.articles)} articles in {source_url}")
        articles = [article.url for article in paper.articles]

    if not articles:
        logging.info(f"No articles found for source: {source_url}")
        return

    tasks = []
    articles_processed = 0
    for article_url in articles:
        if download_all and articles_processed >= MAX_ARTICLES_PER_SOURCE:
            break
        task = asyncio.create_task(
            process_article_with_timeout(
                article_url, global_patterns, source_patterns, download_all
            )
        )
        tasks.append(task)
        if download_all:
            articles_processed += 1

    results = await asyncio.gather(*tasks)
    articles_added = sum(results)
    logging.info(f"Added {articles_added} articles from {source_url}")


async def process_article_with_timeout(
    article_url, global_patterns, source_patterns, download_all
):
    try:
        return await asyncio.wait_for(
            process_article(
                article_url, global_patterns, source_patterns, download_all
            ),
            timeout=30,  # Adjust this value as needed
        )
    except asyncio.TimeoutError:
        logging.warning(f"Processing timed out for article: {article_url}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_articles())
