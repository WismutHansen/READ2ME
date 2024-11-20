import sqlite3
import os
import uuid
from database.crud import generate_hash  # Use your existing hash function

# Database path
DATABASE_DIR = "database"
DATABASE_PATH = os.path.join(DATABASE_DIR, "read2me.db")


def recreate_table_with_new_ids():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Step 1: Create new tables with the updated schema, including `old_id` temporarily
        cursor.execute("""
            CREATE TABLE texts_new (
                id TEXT PRIMARY KEY,
                old_id INTEGER,
                title TEXT,
                text TEXT,
                date_added DATE,
                language TEXT,
                tl_dr TEXT,
                audio_file TEXT,
                markdown_file TEXT,
                img_file TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE podcasts_new (
                id TEXT PRIMARY KEY,
                old_id INTEGER,
                title TEXT,
                text TEXT,
                date_added DATE,
                language TEXT,
                audio_file TEXT,
                markdown_file TEXT,
                img_file TEXT
            );
        """)

        print("New tables created.")

        # Step 2: Dynamically fetch column names
        cursor.execute("PRAGMA table_info(texts);")
        old_text_columns = [info[1] for info in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(texts_new);")
        new_text_columns = [info[1] for info in cursor.fetchall()]

        cursor.execute("PRAGMA table_info(podcasts);")
        old_podcast_columns = [info[1] for info in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(podcasts_new);")
        new_podcast_columns = [info[1] for info in cursor.fetchall()]

        # Step 3: Copy data for `texts`
        seen_ids = set()
        cursor.execute(f"SELECT {', '.join(old_text_columns)} FROM texts")
        rows = cursor.fetchall()
        for row in rows:
            old_id = row[0]
            unique_input = f"{old_id}-{row[1]}-{row[3]}"
            new_id = generate_hash(unique_input)

            # Ensure uniqueness by appending UUID if necessary
            while new_id in seen_ids:
                new_id = f"{generate_hash(unique_input)}-{uuid.uuid4().hex[:6]}"

            seen_ids.add(new_id)
            data = (new_id, old_id) + tuple(row[1 : len(new_text_columns) - 1])
            cursor.execute(
                f"INSERT INTO texts_new ({', '.join(new_text_columns)}) VALUES ({', '.join(['?'] * len(new_text_columns))})",
                data,
            )

        print("Data copied into new texts table.")

        # Step 4: Copy data for `podcasts`
        seen_ids = set()
        cursor.execute(f"SELECT {', '.join(old_podcast_columns)} FROM podcasts")
        rows = cursor.fetchall()
        for row in rows:
            old_id = row[0]
            unique_input = f"{old_id}-{row[1]}-{row[3]}"
            new_id = generate_hash(unique_input)

            # Ensure uniqueness by appending UUID if necessary
            while new_id in seen_ids:
                new_id = f"{generate_hash(unique_input)}-{uuid.uuid4().hex[:6]}"

            seen_ids.add(new_id)
            data = (new_id, old_id) + tuple(row[1 : len(new_podcast_columns) - 1])
            cursor.execute(
                f"INSERT INTO podcasts_new ({', '.join(new_podcast_columns)}) VALUES ({', '.join(['?'] * len(new_podcast_columns))})",
                data,
            )

        print("Data copied into new podcasts table.")

        # Step 5: Update relationships in `seed_text`
        cursor.execute("""
            UPDATE seed_text
            SET text_id = (
                SELECT id FROM texts_new WHERE texts_new.old_id = seed_text.text_id
            ),
            podcast_id = (
                SELECT id FROM podcasts_new WHERE podcasts_new.old_id = seed_text.podcast_id
            )
        """)
        print("Relationships updated in seed_text.")

        # Step 6: Drop old tables before renaming
        cursor.execute("DROP TABLE IF EXISTS texts;")
        cursor.execute("DROP TABLE IF EXISTS podcasts;")

        cursor.execute("ALTER TABLE texts_new RENAME TO texts;")
        cursor.execute("ALTER TABLE podcasts_new RENAME TO podcasts;")
        print("Old tables replaced with new tables.")

        conn.commit()
        print("Migration completed successfully.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error during migration: {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    recreate_table_with_new_ids()
