import json
import os
import argparse
from typing import List, Optional, Dict, Union, Tuple
from urllib.parse import urlparse
from .rssfeed import find_rss_feed

SOURCES_FILE = "sources.json"
MY_FEEDS_FILE = "my_feeds.json"

def read_sources() -> Dict:
    if not os.path.exists(SOURCES_FILE):
        return {"global_keywords": [], "sources": []}
    with open(SOURCES_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {"global_keywords": [], "sources": []}

def read_feeds() -> Dict:
    if not os.path.exists(MY_FEEDS_FILE):
        return {"feeds": []}
    with open(MY_FEEDS_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {"feeds": []}

def write_sources(data: Dict):
    with open(SOURCES_FILE, "w") as file:
        json.dump(data, file, indent=2)

def write_feeds(data: Dict):
    with open(MY_FEEDS_FILE, "w") as file:
        json.dump(data, file, indent=2)

def get_site_name(url: str) -> str:
    """Extract a readable name from the URL."""
    parsed = urlparse(url)
    # Remove www. if present and get the domain name
    domain = parsed.netloc.replace("www.", "")
    # Take first part of domain (before first dot) and capitalize
    return domain.split(".")[0].title()

def print_sources():
    data = read_sources()
    if not data["sources"]:
        print("No source has been added to the directory yet")
    else:
        print("Global Keywords:", ", ".join(data["global_keywords"]))
        print("\nSources:")
        for source in data["sources"]:
            keywords = source["keywords"]
            if keywords == ["*"]:
                keyword_str = "* (all articles)"
            elif not keywords:
                keyword_str = "No source-specific keywords"
            else:
                keyword_str = ", ".join(keywords)
            print(f" URL: {source['url']}")
            print(f" Keywords: {keyword_str}")
            print(f" Is RSS Feed: {source.get('is_rss', False)}")
            print()

def update_sources(
    global_keywords: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, Union[str, List[str], bool]]]] = None,
) -> Tuple[Dict, bool]:
    """Update sources and return both the updated data and whether a refresh is needed.
    
    Returns:
        Tuple[Dict, bool]: (updated_data, needs_refresh)
    """
    data = read_sources()
    added_rss_feed = False
    
    if global_keywords is not None:
        data["global_keywords"] = list(set(data["global_keywords"] + global_keywords))
    if sources is not None:
        for new_source in sources:
            # Convert Pydantic model to dict if needed
            if hasattr(new_source, "model_dump"):
                new_source = new_source.model_dump()
            elif hasattr(new_source, "dict"):
                new_source = new_source.dict()
                
            existing_source = next(
                (s for s in data["sources"] if s["url"] == new_source["url"]), None
            )
            rss_feed_url = find_rss_feed(new_source["url"])
            if rss_feed_url:
                new_source["url"] = rss_feed_url
                new_source["is_rss"] = True
                
                # Also add to my_feeds.json if it's an RSS feed
                feeds_data = read_feeds()
                if not any(feed["url"] == rss_feed_url for feed in feeds_data["feeds"]):
                    feeds_data["feeds"].append({
                        "category": new_source.get("category", "General"),
                        "name": new_source.get("name", get_site_name(rss_feed_url)),
                        "url": rss_feed_url
                    })
                    write_feeds(feeds_data)
                    added_rss_feed = True
            else:
                new_source["is_rss"] = False
                
            if existing_source:
                existing_source["keywords"] = new_source["keywords"]
                existing_source["category"] = new_source.get("category", "General")
                existing_source["is_rss"] = new_source["is_rss"]
            else:
                if "category" not in new_source:
                    new_source["category"] = "General"
                data["sources"].append(new_source)

    write_sources(data)
    return data, added_rss_feed

def remove_source(url: str) -> Dict:
    data = read_sources()
    data["sources"] = [s for s in data["sources"] if s["url"] != url]
    write_sources(data)
    return data

def remove_global_keyword(keyword: str) -> Dict:
    data = read_sources()
    data["global_keywords"] = [k for k in data["global_keywords"] if k != keyword]
    write_sources(data)
    return data

def cli():
    parser = argparse.ArgumentParser(
        description="Manage sources and keywords for article fetching"
    )
    parser.add_argument("--add-global", nargs="+", help="Add global keywords")
    parser.add_argument(
        "--add-source",
        nargs=2,
        metavar=("URL", "KEYWORDS"),
        action="append",
        help="Add a source with keywords",
    )
    parser.add_argument("--remove-source", metavar="URL", help="Remove a source by URL")
    parser.add_argument(
        "--remove-global", metavar="KEYWORD", help="Remove a global keyword"
    )
    parser.add_argument("--list", action="store_true", help="List all sources")

    args = parser.parse_args()

    if args.list:
        print_sources()
    elif args.add_global:
        update_sources(global_keywords=args.add_global)
        print("Global keywords added.")
    elif args.add_source:
        sources = [
            {"url": url, "keywords": keywords.split(",")}
            for url, keywords in args.add_source
        ]
        update_sources(sources=sources)
        print("Sources added.")
    elif args.remove_source:
        remove_source(args.remove_source)
        print("Source removed.")
    elif args.remove_global:
        remove_global_keyword(args.remove_global)
        print("Global keyword removed.")
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()
