import newspaper
import os
import re
from .task_file_handler import add_task
from dotenv import load_dotenv

load_dotenv()
sources_file = os.getenv("SOURCES_FILE")
keywords_file = os.getenv("KEYWORDS_FILE")

# Function to read URLs from a file
def read_urls_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
            print(f"Read {len(urls)} URLs from {file_path}")
            return urls
    except Exception as e:
        print(f"Error reading URLs from file: {e}")
        return []

# Function to read keywords from a file
def read_keywords_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            keywords = [line.strip().lower() for line in file if line.strip()]
            print(f"Read {len(keywords)} keywords from {file_path}")
            return keywords
    except Exception as e:
        print(f"Error reading keywords from file: {e}")
        return []

# Read URLs and keywords from files
if not sources_file:
    print("SOURCES_FILE environment variable not set.")
else:
    source_urls = read_urls_from_file(sources_file)

if not keywords_file:
    print("KEYWORDS_FILE environment variable not set.")
else:
    keywords = read_keywords_from_file(keywords_file)

# Compile regular expressions for keywords, ensuring whole word matches
keyword_patterns = [re.compile(r'\b' + re.escape(keyword).replace('\\ ', '\\s+') + r'\b') for keyword in keywords]

# Debugging: print the regex patterns
print("Compiled regex patterns:")
for pattern in keyword_patterns:
    print(pattern.pattern)

if sources_file and keywords_file:
    # Fetch articles from each source
    for source_url in source_urls:
        print(f"Building newspaper object for source: {source_url}")
        paper = newspaper.build(source_url, number_threads=3, memoize_articles=False)
        print(f"Found {len(paper.articles)} articles in {source_url}")

        # Collect article URLs
        article_urls = [article.url for article in paper.articles]
        print(f"Found {len(article_urls)} article URLs in {source_url}")

        for article_url in article_urls:
            try:
                # Debugging: print article URL
                print(f"Article URL: {article_url}")
                
                # Replace hyphens with spaces in the article URL
                article_url = article_url.replace('-', ' ').lower()
                print(f"Processing article URL: {article_url}")

                # Check if any keyword pattern is present in the article URL
                matched = False
                for pattern in keyword_patterns:
                    if pattern.search(article_url):
                        matched = True
                        print(f"Keyword '{pattern.pattern}' found in URL: {article_url}")
                        add_task('url', article_url, 'edge_tts')
                        break
                
                if not matched:
                    print(f"No keywords found in URL: {article_url}")

            except Exception as e:
                print(f"Failed to process article {article_url}: {e}")

# Debugging: Show completion message
print("Completed processing all sources and articles.")
