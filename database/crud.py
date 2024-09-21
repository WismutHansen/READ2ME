import sqlite3
from datetime import datetime
import hashlib
import base64
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, "read2me.db")


def create_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


def create_article(article_data: dict, author_names: list = None):
    conn = create_connection()
    cursor = conn.cursor()
    
    # Ensure `date_published` is properly formatted or set to None
    date_published = article_data.get("date_published")
    if date_published:
        try:
            date_published = datetime.strptime(date_published, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            date_published = None  # Invalid format, set to None
    else:
        date_published = None
    
    # Insert article into the database
    cursor.execute(
        """
        INSERT INTO articles (id, url, title, date_published, date_added, language, plain_text, markdown_text, tl_dr, audio_file, markdown_file, vtt_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generate_hash(article_data["url"]),
            article_data["url"],
            article_data["title"],
            date_published,  # Use the properly formatted or None value
            article_data.get("date_added", datetime.today().strftime("%Y-%m-%d")),
            article_data.get("language"),
            article_data.get("plain_text"),
            article_data.get("markdown_text"),
            article_data.get("tl_dr"),
            article_data.get("audio_file"),
            article_data.get("markdown_file"),
            article_data.get("vtt_file"),
        ),
    )

    article_id = generate_hash(article_data["url"])

    # Handle author association
    if author_names:
        for author_name in author_names:
            cursor.execute(
                """
                SELECT id FROM authors WHERE name = ?
                """,
                (author_name,),
            )
            author = cursor.fetchone()
            if author:
                author_id = author[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO authors (name) VALUES (?)
                    """,
                    (author_name,),
                )
                author_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO article_author (article_id, author_id)
                VALUES (?, ?)
                """,
                (article_id, author_id),
            )

    conn.commit()
    conn.close()


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


def create_text(text_data: dict):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO texts (id, text, date_added, language, plain_text)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            generate_hash(text_data["text"]),
            text_data["text"],
            text_data.get("date_added", datetime.today().strftime("%Y-%m-%d")),
            text_data.get("language"),
            text_data.get("plain_text"),
        ),
    )
    conn.commit()
    conn.close()


def generate_hash(value: str) -> str:
    hash_object = hashlib.sha256(value.encode())
    hash_digest = hash_object.digest()
    return str(base64.urlsafe_b64encode(hash_digest)[:6].decode("utf-8"))


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


def update_article(article_id: str, updated_fields: dict):
    if not updated_fields:
        print("No fields to update.")
        return

    conn = create_connection()
    cursor = conn.cursor()

    # Generate the SQL query dynamically
    set_clause = ", ".join([f"{field} = ?" for field in updated_fields.keys()])
    values = list(updated_fields.values())
    values.append(article_id)

    query = f"""
        UPDATE articles
        SET {set_clause}
        WHERE id = ?
    """

    cursor.execute(query, values)
    conn.commit()
    conn.close()

    print(f"Article with id '{article_id}' has been updated.")

    return (
        cursor.rowcount
    )  # Returns the number of rows affected (should be 1 if successful)


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
    article_data = {
        "url": url,
        "title": title,
        "date_published": date_published,
        "language": language,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "tl_dr": tl_dr,
        "audio_file": audio_file,
        "markdown_file": markdown_file,
        "vtt_file": vtt_file,
    }
    create_article(article_data)
    print(f"Article '{title}' has been successfully added to the database.")


if __name__ == "__main__":
    main()
