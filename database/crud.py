import base64
import hashlib
import os
import sqlite3
from datetime import datetime, date
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

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
    text: Optional[str] = None
    title: Optional[str] = None
    date_added: Optional[str] = date.today().strftime("%Y-%m-%d")
    language: Optional[str] = None
    tl_dr: Optional[str] = None
    audio_file: Optional[str] = None
    markdown_file: Optional[str] = None
    img_file: Optional[str] = None


class PodcastData(BaseModel):
    url: Optional[HttpUrl] = None
    title: Optional[str] = None
    date_published: Optional[str] = None
    date_added: Optional[str] = date.today().strftime("%Y-%m-%d")
    language: Optional[str] = None
    text: Optional[str] = None
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


def fetch_available_media():
    conn = create_connection()
    cursor = conn.cursor()
    media = []

    # Fetch articles with audio
    cursor.execute("""
        SELECT articles.id, articles.title, articles.date_added, articles.date_published,
               group_concat(authors.name), articles.audio_file, 'article'
        FROM articles
        LEFT JOIN article_author ON articles.id = article_author.article_id
        LEFT JOIN authors ON article_author.author_id = authors.id
        WHERE articles.audio_file IS NOT NULL
        GROUP BY articles.id
    """)
    articles = cursor.fetchall()
    media.extend(articles)

    # Fetch podcasts with audio
    cursor.execute("""
        SELECT podcasts.id, podcasts.title, podcasts.date_added, NULL, NULL,
               podcasts.audio_file, 'podcast'
        FROM podcasts
        WHERE podcasts.audio_file IS NOT NULL
    """)
    podcasts = cursor.fetchall()
    media.extend(podcasts)

    # Fetch texts with audio
    cursor.execute("""
        SELECT texts.id, texts.title, texts.date_added, NULL, NULL,
               texts.audio_file, 'text'
        FROM texts
        WHERE texts.audio_file IS NOT NULL
    """)
    texts = cursor.fetchall()
    media.extend(texts)

    conn.close()

    # Format combined media records
    return [
        AvailableMedia(
            id=str(row[0]),  # Convert ID to string
            title=row[1],
            date_added=row[2],
            date_published=row[3],
            authors=row[4].split(",") if row[4] else [],
            audio_file=row[5],
            content_type=row[6],
        )
        for row in media
    ]


def create_article(article_data: ArticleData, authors: Optional[List[Author]] = None):
    conn = create_connection()
    cursor = conn.cursor()

    # Ensure date_published has a default if None
    date_published = article_data.date_published or datetime.today().strftime(
        "%Y-%m-%d"
    )
    # Generate the article ID from the URL
    article_id = generate_hash(str(article_data.url))
    try:
        cursor.execute(
            """
            INSERT INTO articles (id, url, title, date_published, date_added, language, plain_text, markdown_text, tl_dr, audio_file, markdown_file, vtt_file, img_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                str(article_data.url),
                article_data.title,
                date_published,
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
        conn.commit()
    except sqlite3.Error as e:
        print(f"Couldn't add article data to database: {e}")
    finally:
        conn.close()
    return article_id


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
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM articles WHERE id = ?
    """,
        (article_id,),
    )
    article = cursor.fetchone()
    conn.close()
    return article


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


def create_text(text_data: TextData):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO texts (title, text, date_added, language, tl_dr, audio_file, markdown_file, img_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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

        # Retrieve the auto-generated ID of the newly inserted text
        text_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"Could not add text data to the database: {e}")
        text_id = (
            None  # Handle error by setting text_id to None or other error handling
        )
    finally:
        conn.close()

    return text_id


def update_text(text_id: int, updated_fields: TextData):
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
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM texts WHERE id = ?
        """,
        (int(text_id),),  # Convert ID to integer
    )
    text = cursor.fetchone()
    conn.close()
    return text


def create_podcast_db_entry(
    podcast_data: PodcastData,
    seed_text_id: Optional[str] = None,
    seed_article_id: Optional[str] = None,
) -> int:
    conn = create_connection()
    cursor = conn.cursor()

    # Insert the podcast data, letting SQLite handle the ID generation
    cursor.execute(
        """
        INSERT INTO podcasts (title, text, date_added, language, audio_file, markdown_file, img_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            podcast_data.title,
            podcast_data.text,
            podcast_data.date_added or datetime.today().strftime("%Y-%m-%d"),
            podcast_data.language,
            podcast_data.audio_file,
            podcast_data.markdown_file,
            podcast_data.img_file,
        ),
    )

    # Retrieve the generated podcast_id for linking
    podcast_id = cursor.lastrowid

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


def update_podcast(podcast_id: int, updated_fields: PodcastData):
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

    print(f"Text with id '{podcast_id}' has been updated.")

    return (
        cursor.rowcount
    )  # Returns the number of rows affected (should be 1 if successful)


def get_podcast(podcast_id: str):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM podcasts WHERE id = ?
        """,
        (int(podcast_id),),  # Convert ID to integer
    )
    podcast = cursor.fetchone()
    conn.close()
    return podcast


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
    url = input("Please enter the article URL: ")
    article_id = generate_hash(url)
    if article_exists(article_id):
        print("An article with this URL already exists in the database.")
        return

    title = input("Please enter the article title: ")
    date_published = (
        input("Please enter the publication date (YYYY-MM-DD, optional): ") or None
    )
    language = input("Please enter the language of the article: ")
    plain_text = input("Please enter the plain text content of the article: ")
    markdown_text = (
        input("Please enter the markdown version of the article (optional): ") or None
    )
    tl_dr = input("Please enter a TL;DR summary (optional): ") or None
    audio_file = input("Please enter the path to the audio file (optional): ") or None
    markdown_file = (
        input("Please enter the path to the markdown file (optional): ") or None
    )
    vtt_file = input("Please enter the path to the VTT file (optional): ") or None

    # Create the article data dictionary
    article_data = ArticleData(
        url=url,
        title=title,
        date_published=date_published,
        language=language,
        plain_text=plain_text,
        markdown_text=markdown_text,
        tl_dr=tl_dr,
        audio_file=audio_file,
        markdown_file=markdown_file,
        vtt_file=vtt_file,
    )

    create_article(article_data)
    print(f"Article '{title}' has been successfully added to the database.")


if __name__ == "__main__":
    print(fetch_available_media())
