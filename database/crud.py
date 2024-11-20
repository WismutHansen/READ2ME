import base64
import hashlib
import os
import sqlite3
from datetime import datetime, date
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, "read2me.db")


def create_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


class ArticleData(BaseModel):
    url: Optional[HttpUrl] = None
    title: Optional[str] = None
    date_published: Optional[str] = None
    date_added: Optional[str] = date.today().strftime("%Y-%m-%d")
    language: Optional[str] = None
    plain_text: Optional[str] = None
    markdown_text: Optional[str] = None
    tl_dr: Optional[str] = None
    audio_file: Optional[str] = None
    markdown_file: Optional[str] = None
    vtt_file: Optional[str] = None
    img_file: Optional[str] = None


class TextData(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    date_added: Optional[str] = date.today().strftime("%Y-%m-%d")
    language: Optional[str] = None
    tl_dr: Optional[str] = None
    audio_file: Optional[str] = None
    markdown_file: Optional[str] = None
    img_file: Optional[str] = None


class PodcastData(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    date_added: Optional[str] = date.today().strftime("%Y-%m-%d")
    language: Optional[str] = None
    audio_file: Optional[str] = None
    markdown_file: Optional[str] = None
    img_file: Optional[str] = None


class Author(BaseModel):
    id: str
    name: str


class AvailableMedia(BaseModel):
    id: str
    title: Optional[str] = None
    date_added: str
    date_published: Optional[str] = None
    language: Optional[str] = None
    authors: Optional[List[str]] = []
    audio_file: Optional[str]
    content_type: str
    url: Optional[str] = None


def fetch_available_media():
    conn = create_connection()
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    cursor = conn.cursor()
    media = []

    # Fetch articles with audio
    cursor.execute("""
        SELECT 
            articles.id,
            articles.title,
            articles.date_added,
            articles.date_published,
            GROUP_CONCAT(authors.name) as authors,
            articles.audio_file,
            articles.url,
            'article' as content_type
        FROM articles
        LEFT JOIN article_author ON articles.id = article_author.article_id
        LEFT JOIN authors ON article_author.author_id = authors.id
        WHERE articles.audio_file IS NOT NULL
        GROUP BY articles.id
    """)
    media.extend(cursor.fetchall())

    # Fetch podcasts with audio
    cursor.execute("""
        SELECT 
            id,
            title,
            date_added,
            NULL as date_published,
            NULL as authors,
            audio_file,
            NULL as url,
            'podcast' as content_type
        FROM podcasts
        WHERE audio_file IS NOT NULL
    """)
    media.extend(cursor.fetchall())

    # Fetch texts with audio
    cursor.execute("""
        SELECT 
            id,
            title,
            date_added,
            NULL as date_published,
            NULL as authors,
            audio_file,
            NULL as url,
            'text' as content_type
        FROM texts
        WHERE audio_file IS NOT NULL
    """)
    media.extend(cursor.fetchall())

    conn.close()

    # Format combined media records
    return [
        AvailableMedia(
            id=dict(row)["id"],
            title=row["title"],
            date_added=row["date_added"],
            date_published=row["date_published"],
            authors=row["authors"].split(",") if row["authors"] else [],
            audio_file=row["audio_file"],
            content_type=row["content_type"],
            url=row["url"],
        )
        for row in media
    ]


def create_article(article_data: ArticleData, authors: Optional[List[Author]] = None):
    """Create a new article in the database."""
    conn = create_connection()
    cursor = conn.cursor()

    # Generate a unique ID for the article
    article_id = generate_hash(f"{article_data.url}{datetime.now().isoformat()}")

    # Convert absolute paths to relative paths for storage
    if article_data.audio_file:
        article_data.audio_file = os.path.relpath(
            article_data.audio_file, os.path.abspath(os.getenv("OUTPUT_DIR", "Output"))
        )
    if article_data.markdown_file:
        article_data.markdown_file = os.path.relpath(
            article_data.markdown_file,
            os.path.abspath(os.getenv("OUTPUT_DIR", "Output")),
        )
    if article_data.vtt_file:
        article_data.vtt_file = os.path.relpath(
            article_data.vtt_file, os.path.abspath(os.getenv("OUTPUT_DIR", "Output"))
        )

    try:
        cursor.execute(
            """
            INSERT INTO articles (
                id, url, title, date_published, date_added,
                language, plain_text, markdown_text, tl_dr,
                audio_file, markdown_file, vtt_file, img_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                str(article_data.url) if article_data.url else None,
                article_data.title,
                article_data.date_published,
                article_data.date_added,
                article_data.language,
                article_data.plain_text,
                article_data.markdown_text,
                article_data.tl_dr,
                article_data.audio_file,
                article_data.markdown_file,
                article_data.vtt_file,
                article_data.img_file,
            ),
        )

        # Add authors if provided
        if authors:
            for author in authors:
                add_author(author)
                cursor.execute(
                    "INSERT INTO article_author (article_id, author_id) VALUES (?, ?)",
                    (article_id, author.id),
                )

        conn.commit()
        return article_id
    except sqlite3.Error as e:
        print(f"Error creating article: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def update_article(article_id: str, updated_fields: ArticleData):
    conn = create_connection()
    cursor = conn.cursor()

    # Filter out None values to only update provided fields
    fields_to_update = {
        key: value
        for key, value in updated_fields.model_dump().items()
        if value is not None
    }

    if not fields_to_update:
        print("No fields to update.")
        return

    set_clause = ", ".join([f"{field} = ?" for field in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [article_id]

    query = f"UPDATE articles SET {set_clause} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    print(f"Article with id '{article_id}' has been updated.")


def get_articles(skip: int = 0, limit: int = 100):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM articles ORDER BY date_added DESC LIMIT ? OFFSET ?
    """,
        (limit, skip),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_article(article_id: str):
    conn = create_connection()
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM articles WHERE id = ?
    """,
        (article_id,),
    )
    article = cursor.fetchone()
    conn.close()
    return dict(article) if article else None  # Convert Row to dict if article exists


def get_total_articles():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM articles
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count


def article_exists(article_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1 FROM articles WHERE id = ?
    """,
        (article_id,),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def print_articles_summary():
    conn = create_connection()
    cursor = conn.cursor()

    # Query to join articles with authors and retrieve specific columns
    cursor.execute("""
        SELECT articles.id, articles.title, authors.name, articles.date_published, articles.url
        FROM articles
        LEFT JOIN article_author ON articles.id = article_author.article_id
        LEFT JOIN authors ON article_author.author_id = authors.id
    """)

    rows = cursor.fetchall()
    conn.close()

    # Print out the results
    print(f"{'ID':<10} {'Title':<30} {'Author':<20} {'Date Published':<15} {'URL'}")
    print("-" * 100)

    for row in rows:
        id, title, author, date_published, url = row
        print(f"{id:<10} {title:<30} {author:<20} {date_published:<15} {url}")


def delete_article(article_id: str):
    conn = create_connection()
    cursor = conn.cursor()

    # Delete the article by id
    cursor.execute(
        """
        DELETE FROM articles WHERE id = ?
    """,
        (article_id,),
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return cursor.rowcount


def create_text(text_data: TextData) -> str:
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Generate a unique text ID for the text entry
        text_id = generate_hash(
            f"{text_data.title or ''}{text_data.text or ''}{datetime.now().isoformat()}"
        )

        # Convert absolute paths to relative paths for storage
        if text_data.audio_file:
            text_data.audio_file = os.path.relpath(
                text_data.audio_file, os.path.abspath(os.getenv("OUTPUT_DIR", "Output"))
            )
        if text_data.markdown_file:
            text_data.markdown_file = os.path.relpath(
                text_data.markdown_file,
                os.path.abspath(os.getenv("OUTPUT_DIR", "Output")),
            )

        cursor.execute(
            """
            INSERT INTO texts (id, title, text, date_added, language, tl_dr, audio_file, markdown_file, img_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                text_id,
                text_data.title,
                text_data.text,
                text_data.date_added or datetime.today().strftime("%Y-%m-%d"),
                text_data.language,
                text_data.tl_dr,
                text_data.audio_file,
                text_data.markdown_file,
                text_data.img_file,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Could not add text data to the database: {e}")
        text_id = (
            None  # Handle error by setting text_id to None or other error handling
        )
    finally:
        conn.close()

    return text_id


def update_text(text_id: str, updated_fields: TextData):
    conn = create_connection()
    cursor = conn.cursor()

    # Filter out None values to only update provided fields
    fields_to_update = {
        key: value
        for key, value in updated_fields.model_dump().items()
        if value is not None
    }

    if not fields_to_update:
        print("No fields to update.")
        return

    set_clause = ", ".join([f"{field} = ?" for field in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [text_id]

    query = f"UPDATE texts SET {set_clause} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()

    print(f"Text with id '{text_id}' has been updated.")

    return (
        cursor.rowcount
    )  # Returns the number of rows affected (should be 1 if successful)


def get_text(text_id: str):
    conn = create_connection()
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM texts WHERE id = ?
    """,
        (text_id,),
    )
    text = cursor.fetchone()
    conn.close()
    return dict(text) if text else None  # Convert Row to dict if text exists


def create_podcast_db_entry(
    podcast_data: PodcastData,
    seed_text_id: Optional[str] = None,
    seed_article_id: Optional[str] = None,
) -> str:
    conn = create_connection()
    cursor = conn.cursor()

    # Generate a unique text ID for the podcast
    podcast_id = generate_hash(
        f"{podcast_data.title or ''}{podcast_data.text or ''}{datetime.now().isoformat()}"
    )

    # Convert absolute paths to relative paths for storage
    if podcast_data.audio_file:
        podcast_data.audio_file = os.path.relpath(
            podcast_data.audio_file, os.path.abspath(os.getenv("OUTPUT_DIR", "Output"))
        )
    if podcast_data.markdown_file:
        podcast_data.markdown_file = os.path.relpath(
            podcast_data.markdown_file,
            os.path.abspath(os.getenv("OUTPUT_DIR", "Output")),
        )

    # Insert the podcast data with the generated ID
    cursor.execute(
        """
        INSERT INTO podcasts (id, title, text, date_added, language, audio_file, markdown_file, img_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            podcast_id,
            podcast_data.title,
            podcast_data.text,
            podcast_data.date_added,
            podcast_data.language,
            podcast_data.audio_file,
            podcast_data.markdown_file,
            podcast_data.img_file,
        ),
    )

    # Link podcast to seed text or article if provided
    if seed_text_id or seed_article_id:
        cursor.execute(
            """
            INSERT INTO seed_text (podcast_id, article_id, text_id)
            VALUES (?, ?, ?)
            """,
            (podcast_id, seed_article_id, seed_text_id),
        )

    conn.commit()
    conn.close()
    return podcast_id


def update_podcast(podcast_id: str, updated_fields: PodcastData):
    conn = create_connection()
    cursor = conn.cursor()
    # Filter out None values to only update provided fields
    fields_to_update = {
        key: value
        for key, value in updated_fields.model_dump().items()
        if value is not None
    }

    if not fields_to_update:
        print("No fields to update.")
        return

    set_clause = ", ".join([f"{field} = ?" for field in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [podcast_id]

    query = f"UPDATE podcasts SET {set_clause} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()

    print(f"Podcast with id '{podcast_id}' has been updated.")

    return (
        cursor.rowcount
    )  # Returns the number of rows affected (should be 1 if successful)


def get_podcast(podcast_id: str):
    conn = create_connection()
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM podcasts WHERE id = ?
    """,
        (podcast_id,),
    )
    podcast = cursor.fetchone()
    conn.close()
    return dict(podcast) if podcast else None  # Convert Row to dict if podcast exists


def generate_hash(value: str) -> str:
    hash_object = hashlib.sha256(value.encode())
    hash_digest = hash_object.digest()
    return str(base64.urlsafe_b64encode(hash_digest)[:6].decode("utf-8"))


def add_author(author: Author):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO authors (id, name) VALUES (?, ?)", (author.id, author.name)
        )
        conn.commit()
        print(f"Author {author.name} added successfully.")
    except sqlite3.IntegrityError:
        print(f"Author {author.name} already exists or id conflict.")
    finally:
        conn.close()


def get_author(author_id: str) -> Optional[Author]:
    """
    Retrieves an author by id from the authors table.
    """
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM authors WHERE id = ?", (author_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return Author(id=row[0], name=row[1])
    else:
        print("Author not found.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create or update articles, podcasts, and texts in the database."
    )

    parser.add_argument(
        "action",
        choices=[
            "create_article",
            "update_article",
            "create_text",
            "update_text",
            "create_podcast",
        ],
        help="The action to perform.",
    )
    parser.add_argument(
        "--url",
        type=str,
        required=False,
        help="The URL of the article (for create/update article).",
    )
    parser.add_argument(
        "--title",
        type=str,
        required=False,
        help="The title of the content (article, text, or podcast).",
    )
    parser.add_argument(
        "--date-published",
        type=str,
        required=False,
        help="The publication date of the content (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--language", type=str, required=False, help="The language of the content."
    )
    parser.add_argument(
        "--plain-text", type=str, required=False, help="The plain text content."
    )
    parser.add_argument(
        "--markdown-text", type=str, required=False, help="The Markdown content."
    )
    parser.add_argument("--tl-dr", type=str, required=False, help="The TL;DR summary.")
    parser.add_argument(
        "--audio-file", type=str, required=False, help="The path to the audio file."
    )
    parser.add_argument(
        "--markdown-file",
        type=str,
        required=False,
        help="The path to the Markdown file.",
    )
    parser.add_argument(
        "--vtt-file", type=str, required=False, help="The path to the VTT file."
    )
    parser.add_argument(
        "--text",
        type=str,
        required=False,
        help="The text content (for create/update text).",
    )
    parser.add_argument(
        "--id", type=str, required=False, help="The ID of the content to update."
    )

    args = parser.parse_args()

    if args.action == "create_article":
        create_article(
            ArticleData(
                url=args.url,
                title=args.title,
                date_published=args.date_published,
                language=args.language,
                plain_text=args.plain_text,
                markdown_text=args.markdown_text,
                tl_dr=args.tl_dr,
                audio_file=args.audio_file,
                markdown_file=args.markdown_file,
                vtt_file=args.vtt_file,
            )
        )
    elif args.action == "update_article":
        update_article(
            args.id,
            ArticleData(
                url=args.url,
                title=args.title,
                date_published=args.date_published,
                language=args.language,
                plain_text=args.plain_text,
                markdown_text=args.markdown_text,
                tl_dr=args.tl_dr,
                audio_file=args.audio_file,
                markdown_file=args.markdown_file,
                vtt_file=args.vtt_file,
            ),
        )
    elif args.action == "create_text":
        create_text(
            TextData(
                title=args.title,
                text=args.text,
                language=args.language,
                tl_dr=args.tl_dr,
                audio_file=args.audio_file,
                markdown_file=args.markdown_file,
                img_file=args.vtt_file,
            )
        )
    elif args.action == "update_text":
        update_text(
            args.id,
            TextData(
                title=args.title,
                text=args.text,
                language=args.language,
                tl_dr=args.tl_dr,
                audio_file=args.audio_file,
                markdown_file=args.markdown_file,
                img_file=args.vtt_file,
            ),
        )
    elif args.action == "create_podcast":
        create_podcast_db_entry(
            PodcastData(
                title=args.title,
                text=args.text,
                language=args.language,
                audio_file=args.audio_file,
                markdown_file=args.markdown_file,
                img_file=args.vtt_file,
            )
        )
    else:
        print("Invalid action. Please choose one of the available actions.")


if __name__ == "__main__":
    main()
