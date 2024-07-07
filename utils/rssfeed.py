import feedparser
from datetime import datetime
import pytz
from bs4 import BeautifulSoup as bs4
import requests
import urllib.parse
from feedsearch import search
import logging

def get_articles_from_feed(url):
    feed = feedparser.parse(url)

    # Get the current date and time in UTC
    now = datetime.now(pytz.utc)
    today = now.date()

    print(f"Today's date (UTC): {today}")

    # Check the entries
    today_entries = []
    for entry in feed.entries:
        entry_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc).date()
        # print(f"Entry date: {entry_date}, Title: {entry.title}, Link: {entry.link}")  # DEBUG
        if entry_date == today:
            today_entries.append(entry)

    # Print the filtered entries
    if today_entries:
        for entry in today_entries:
            print(f"Title: {entry.title}")
            print(f"Link: {entry.link}")
            print(f"Published: {entry.published}")
            print()
    else:
        print("No articles published today.")
    
    # Return the links of the entries published today
    return [entry.link for entry in today_entries if 'link' in entry]

def find_rss_feed(url):
    def validate_feed(feed_url):
        f = feedparser.parse(feed_url)
        return len(f.entries) > 0

    possible_feeds = []

    # Add /feed for WordPress sites
    possible_feeds.append(url.rstrip('/') + '/feed')

    # Add /rss for Tumblr sites
    possible_feeds.append(url.rstrip('/') + '/rss')

    # Add feeds/posts/default for Blogger sites
    if 'blogspot.com' in url:
        possible_feeds.append(url.rstrip('/') + '/feeds/posts/default')

    # Add /feed/ before the publication's name for Medium sites
    if 'medium.com' in url:
        parsed_url = urllib.parse.urlparse(url)
        medium_feed_url = f"{parsed_url.scheme}://{parsed_url.netloc}/feed{parsed_url.path}"
        possible_feeds.append(medium_feed_url)

    # For YouTube channels
    if 'youtube.com' in url or 'youtu.be' in url:
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

    # If no valid feed is found with the predefined patterns, try to find feeds from the site's HTML
    # raw = requests.get(url).text
    # html = bs4(raw, 'html.parser')
    # feed_urls = html.findAll("link", rel="alternate")
    # for f in feed_urls:
    #     t = f.get("type", None)
    #     if t and ("rss" in t or "xml" in t):
    #         href = f.get("href", None)
    #         if href and validate_feed(href):
    #             return href

    # return None  # Return None if no valid feed is found

def findfeed(site):
    raw = requests.get(site).text
    result = []
    possible_feeds = []
    html = bs4(raw, 'html.parser')  # Added parser argument for BeautifulSoup
    feed_urls = html.findAll("link", rel="alternate")
    if len(feed_urls) > 1:
        for f in feed_urls:
            t = f.get("type", None)
            if t:
                if "rss" in t or "xml" in t:
                    href = f.get("href", None)
                    if href:
                        possible_feeds.append(href)
    parsed_url = urllib.parse.urlparse(site)
    base = parsed_url.scheme + "://" + parsed_url.hostname
    atags = html.findAll("a")
    for a in atags:
        href = a.get("href", None)
        if href:
            if "xml" in href or "rss" in href or "feed" in href:
                possible_feeds.append(base + href)
    for url in list(set(possible_feeds)):
        f = feedparser.parse(url)
        if len(f.entries) > 0:
            if url not in result:
                result.append(url)
    if result:
        return min(result, key=len)  # Return the shortest URL
    return None  # Return None if no valid feeds are found

if __name__ == "__main__":

    feed = find_rss_feed("https://www.theverge.com")
    if feed:
        print(feed)
        print(get_articles_from_feed(feed))

