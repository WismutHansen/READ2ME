import re
import os
from atproto import Client
from dotenv import load_dotenv
import requests

load_dotenv()
USERNAME = os.environ["BLUESKY_USERNAME"]
PASSWORD = os.environ["BLUESKY_APP_PASSWORD"]


def resolve_handle_to_did(handle: str) -> str:
    """
    Resolves a Bluesky handle (e.g., 'jaz.bsky.social') to its DID using the Bluesky API.

    Args:
        handle (str): The Bluesky handle.

    Returns:
        str: The corresponding DID (Decentralized Identifier).
    """
    url = f"https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={handle}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json().get("did", "")
    else:
        raise Exception(
            f"Failed to resolve handle: {response.status_code} - {response.text}"
        )


def convert_bsky_url_to_at_uri(feed_url: str) -> str:
    """
    Converts a Bluesky feed URL into an AT URI.

    Args:
        feed_url (str): The Bluesky URL (e.g., 'https://bsky.app/profile/jaz.bsky.social/feed/firehose').

    Returns:
        str: The corresponding AT URI (e.g., 'at://did:plc:xyz/app.bsky.feed.generator/firehose').
    """
    match = re.match(r"https://bsky\.app/profile/([^/]+)/feed/([^/]+)", feed_url)

    if not match:
        raise ValueError("Invalid Bluesky feed URL format.")

    handle, feed_name = match.groups()
    creator_did = resolve_handle_to_did(handle)

    if not creator_did:
        raise Exception(f"Could not resolve DID for handle: {handle}")

    return f"at://{creator_did}/app.bsky.feed.generator/{feed_name}"


def convert_feed_url_to_at_uri(feed_url: str) -> str:
    """
    Converts a Bluesky feed URL with a DID into an AT URI.

    Args:
        feed_url (str): The Bluesky feed URL (e.g., 'https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/feed/with-friends').

    Returns:
        str: The corresponding AT URI (e.g., 'at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/with-friends').
    """
    match = re.match(
        r"https://bsky\.app/profile/(did:plc:[a-z0-9]+)/feed/([^/]+)", feed_url
    )

    if not match:
        raise ValueError("Invalid Bluesky feed URL format.")

    did, feed_name = match.groups()

    return f"at://{did}/app.bsky.feed.generator/{feed_name}"


def fetch_public_feed(feed_uri: str, limit: int = 30):
    """
    Fetches posts from a public feed generator on Bluesky.

    Args:
        feed_uri (str): The URI of the feed generator.
        limit (int): The number of posts to fetch. Default is 30.

    Returns:
        list: A list of posts containing metadata such as content, author, and timestamp.
    """
    client = Client()
    client.login(USERNAME, PASSWORD)

    try:
        # Fetch posts from the public feed generator
        data = client.app.bsky.feed.get_feed({"feed": feed_uri, "limit": limit})

        posts = data.feed
        result = []

        for post in posts:
            record = post.post.record  # The post record object
            author = post.post.author.handle  # The author's handle

            # Corrected direct attribute access
            content = getattr(record, "text", "")  # Post content
            timestamp = getattr(record, "created_at", "")  # Post timestamp

            result.append(
                {
                    "content": content,  # Post content
                    "author": author,  # Author handle
                    "timestamp": timestamp,  # Timestamp of the post
                }
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to fetch public feed: {e}")


# Example usage
if __name__ == "__main__":
    # Public feed generator (replace with relevant feed URI)
    feed_url = (
        "https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/feed/with-friends"
    )
    feed_uri = convert_feed_url_to_at_uri(feed_url)

    news_posts = fetch_public_feed(feed_uri)
    for post in news_posts:
        print(f"{post['timestamp']} - {post['author']}: {post['content']}")
