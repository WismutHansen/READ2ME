import sqlite3
from datetime import date
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, "read2me.db")


def create_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        url TEXT,
        title TEXT,
        date_published DATE,
        date_added DATE DEFAULT CURRENT_DATE,
        language TEXT,
        plain_text TEXT,
        markdown_text TEXT,
        tl_dr TEXT,
        audio_file TEXT,
        markdown_file TEXT,
        vtt_file TEXT,
        img_file TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS texts (
        id TEXT PRIMARY KEY,
        text TEXT,
        date_added DATE DEFAULT CURRENT_DATE,
        language TEXT,
        plain_text TEXT,
        img_file TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT,
        text TEXT,
        chapters TEXT,
        date_added DATE DEFAULT CURRENT_DATE,
        language TEXT,
        epub_file TEXT,
        img_file TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS article_author (
        article_id TEXT,
        author_id TEXT,
        FOREIGN KEY(article_id) REFERENCES articles(id),
        FOREIGN KEY(author_id) REFERENCES authors(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS podcasts (
        id TEXT PRIMARY KEY,
        title TEXT,
        text TEXT,
        date_added DATE DEFAULT CURRENT_DATE,
        language TEXT,
        plain_text TEXT
        audio_file TEXT,
        markdown_file TEXT,
        img_file TEXT

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seed_text (
        podcast_id TEXT,
        article_id TEXT,
        text_id TEXT,
        FOREIGN KEY(podcast_id) REFERENCES podcasts(id),
        FOREIGN KEY(article_id) REFERENCES articles(id),
        FOREIGN KEY(text_id) REFERENCES texts(id)
    )
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
