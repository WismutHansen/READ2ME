from bs4 import BeautifulSoup


def remove_think_tags(text: str) -> str:
    """
    Remove <think> tags and all their inner content from the provided HTML text.

    Parameters:
        text (str): The HTML string to process.

    Returns:
        str: The HTML string with <think> tags and their contents removed.
    """
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all("think"):
        tag.decompose()
    return str(soup)
