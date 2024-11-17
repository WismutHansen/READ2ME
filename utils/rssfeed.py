import feedparser
from datetime import datetime
import pytz
import urllib.parse
from feedsearch import search
import logging
import json
import os
import tldextract


def load_feeds_from_json(file_path="my_feeds.json"):
    """Load feed URLs and categories from JSON file."""
    if not os.path.isfile(file_path):
        logging.error(f"{file_path} does not exist.")
        return []

    with open(file_path, "r") as f:
        try:
            data = json.load(f)
            return [
                {"url": feed["url"], "category": feed["category"]}
                for feed in data["feeds"]
            ]
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {file_path}: {e}")
            return []


def get_articles_from_feed(url, category):
    """Fetch articles published today from a given RSS feed URL."""
    feed = feedparser.parse(url)
    today = datetime.now(pytz.utc).date()
    # We use tldextract to extract the main domain name from a URL
    domainname = tldextract.extract(url)
    main_domain = f"{domainname.domain}.{domainname.suffix}"
    
    today_entries = []
    for entry in feed.entries:
        try:
            # Try different date fields that feeds might use
            date_tuple = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                date_tuple = entry.published_parsed
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                date_tuple = entry.updated_parsed
            elif hasattr(entry, 'created_parsed') and entry.created_parsed:
                date_tuple = entry.created_parsed
            
            if date_tuple and len(date_tuple) >= 6:
                entry_date = datetime(*date_tuple[:6], tzinfo=pytz.utc).date()
                if entry_date == today:
                    today_entries.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": datetime(*date_tuple[:6], tzinfo=pytz.utc).isoformat(),
                        "category": category,
                        "source": main_domain,
                    })
        except (AttributeError, TypeError, ValueError) as e:
            logging.warning(f"Error processing entry from {url}: {str(e)}")
            continue
    
    return today_entries


def find_rss_feed(url):
    def validate_feed(feed_url):
        f = feedparser.parse(feed_url)
        return len(f.entries) > 0

    possible_feeds = []

    # Add /feed for WordPress sites
    possible_feeds.append(url.rstrip("/") + "/feed")

    # Add /rss for Tumblr sites
    possible_feeds.append(url.rstrip("/") + "/rss")

    # Add feeds/posts/default for Blogger sites
    if "blogspot.com" in url:
        possible_feeds.append(url.rstrip("/") + "/feeds/posts/default")

    # Add /feed/ before the publication's name for Medium sites
    if "medium.com" in url:
        parsed_url = urllib.parse.urlparse(url)
        medium_feed_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}/feed{parsed_url.path}"
        )
        possible_feeds.append(medium_feed_url)

    # For YouTube channels
    if "youtube.com" in url or "youtu.be" in url:
        possible_feeds.append(url)

    # Validate each possible feed URL
    for feed_url in possible_feeds:
        if validate_feed(feed_url):
            return feed_url

    try:
        feeds = search(url, as_urls=True)
        if feeds:
            return min(feeds, key=len)  # Return the shortest URL
        else:
            return None

    except Exception as e:
        logging.error(f"Unable to find rrs feed for url: {e}")
        return None


if __name__ == "__main__":
    feeds = load_feeds_from_json()  # Load feed URLs from feeds.json

    all_todays_articles = []

    for feed_url in feeds:
        print(f"Checking feed: {feed_url}")
        todays_articles = get_articles_from_feed(feed_url["url"], feed_url["category"])
        all_todays_articles.extend(todays_articles)

    if all_todays_articles:
        print("\nToday's articles from all feeds:")
        for article in all_todays_articles:
            print(article)
    else:
        print("No articles published today across all feeds.")
