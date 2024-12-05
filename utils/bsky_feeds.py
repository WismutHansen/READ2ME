from atproto import Client


def fetch_public_feed(feed_uri: str, limit: int = 30):
    """
    Fetches posts from a public feed generator on Bluesky.

    Args:
        feed_uri (str): The URI of the feed generator (e.g., for a topic like "tech-news").
        limit (int): The number of posts to fetch. Default is 30.

    Returns:
        list: A list of posts containing metadata such as content, author, and timestamp.
    """
    client = Client()

    try:
        # Fetch posts from the public feed generator
        data = client.app.bsky.feed.get_feed({"feed": feed_uri, "limit": limit})

        posts = data.feed
        result = []

        for post in posts:
            result.append(
                {
                    "content": post.record.get("text", ""),  # Post content
                    "author": post.author.handle,  # Author handle
                    "timestamp": post.record.get(
                        "createdAt", ""
                    ),  # Timestamp of the post
                }
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to fetch public feed: {e}")


# Example usage
if __name__ == "__main__":
    # Public feed generator for "What's Hot" (replace with relevant feed URI)
    feed_uri = "at://did:plc:jfhpnnst6flqway4eaeqzj2a/feed/for-science"

    news_posts = fetch_public_feed(feed_uri)
    for post in news_posts:
        print(f"{post['timestamp']} - {post['author']}: {post['content']}")
