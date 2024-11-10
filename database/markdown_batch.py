from llm.LLM_calls import to_markdown
from database.crud import get_articles, get_article
import random


def make_markdown(text: str) -> str:
    """
    Convert plain text to basic markdown format.
    Handles paragraphs, headers, and basic formatting.
    """
    if not text:
        return ""

    # Split text into paragraphs
    paragraphs = text.split("\n\n")
    formatted_text = []

    for para in paragraphs:
        # Strip whitespace
        para = para.strip()

        if not para:
            continue

        # Check if paragraph looks like a header (short, ends with period)
        if len(para) < 100 and para.endswith("."):
            formatted_text.append(f"## {para}\n")
        # Format quotes (paragraphs starting with quotation marks)
        elif para.startswith('"') and para.endswith('"'):
            formatted_text.append(f"> {para}\n")
        # Format lists (lines starting with - or *)
        elif para.startswith(("-", "*")):
            formatted_text.append(para + "\n")
        # Regular paragraphs
        else:
            formatted_text.append(para + "\n\n")

    return "".join(formatted_text)


def get_random_article():
    """
    Get a random article using the existing get_articles function
    """
    articles = get_articles()  # Using your existing function

    if not articles:
        print("No articles found in the database.")
        return None

    return random.choice(articles)


def main():
    # Fetch random article
    article = get_random_article()

    if not article:
        return

    # Based on your database schema, article is a tuple with all fields
    # We need to find the index of plain_text and title in the tuple
    article_id = article[0]  # Assuming ID is the first column
    title = article[2]  # Assuming title is the third column
    plain_text = article[6]  # Assuming plain_text is the seventh column

    print(f"Selected Article: {title}")
    print(f"ID: {article_id}")
    print("\n" + "=" * 50 + "\n")

    # Convert to markdown and print
    markdown_text = to_markdown(plain_text)
    print(plain_text)
    print("\n----------------------------------\n")
    print(markdown_text)


if __name__ == "__main__":
    main()
