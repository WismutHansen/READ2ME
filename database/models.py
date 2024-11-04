import sqlite3
from datetime import date
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, "read2me.db")


def create_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


def get_existing_columns(cursor, table_name):
    """Fetches existing column names for a given table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {info[1] for info in cursor.fetchall()}


def create_or_update_tables():
    conn = create_connection()
    cursor = conn.cursor()

    # Define the required columns for each table
    required_columns = {
        "articles": [
            ("id", "TEXT PRIMARY KEY"),
            ("url", "TEXT"),
            ("title", "TEXT"),
            ("date_published", "DATE"),
            ("date_added", "DATE DEFAULT CURRENT_DATE"),
            ("language", "TEXT"),
            ("plain_text", "TEXT"),
            ("markdown_text", "TEXT"),
            ("tl_dr", "TEXT"),
            ("audio_file", "TEXT"),
            ("markdown_file", "TEXT"),
            ("vtt_file", "TEXT"),
            ("img_file", "TEXT"),
        ],
        "authors": [
            ("id", "TEXT PRIMARY KEY"),
            ("name", "TEXT UNIQUE"),
        ],
        "texts": [
            ("id", "TEXT PRIMARY KEY"),
            ("text", "TEXT"),
            ("title", "TEXT"),
            ("date_added", "DATE DEFAULT CURRENT_DATE"),
            ("language", "TEXT"),
            ("tl_dr", "TEXT"),
            ("audio_file", "TEXT"),
            ("markdown_file", "TEXT"),
            ("img_file", "TEXT"),
        ],
        "books": [
            ("id", "TEXT PRIMARY KEY"),
            ("title", "TEXT"),
            ("text", "TEXT"),
            ("chapters", "TEXT"),
            ("date_added", "DATE DEFAULT CURRENT_DATE"),
            ("language", "TEXT"),
            ("epub_file", "TEXT"),
            ("audio_file", "TEXT"),
            ("img_file", "TEXT"),
        ],
        "article_author": [
            ("article_id", "TEXT"),
            ("author_id", "TEXT"),
        ],
        "podcasts": [
            ("id", "TEXT PRIMARY KEY"),
            ("title", "TEXT"),
            ("text", "TEXT"),
            ("date_added", "DATE DEFAULT CURRENT_DATE"),
            ("language", "TEXT"),
            ("audio_file", "TEXT"),
            ("markdown_file", "TEXT"),
            ("img_file", "TEXT"),
        ],
        "seed_text": [
            ("podcast_id", "TEXT"),
            ("article_id", "TEXT"),
            ("text_id", "TEXT"),
        ],
    }

    # Iterate over each table and ensure columns are correct
    for table_name, columns in required_columns.items():
        # Check if the table exists, and if not, create it from scratch
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(f'{col} {col_type}' for col, col_type in columns)})"
        )

        # Get existing columns for the table
        existing_columns = get_existing_columns(cursor, table_name)

        # Add any missing columns
        for col, col_type in columns:
            if col not in existing_columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}")
                print(f"Added missing column '{col}' to table '{table_name}'")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_or_update_tables()
