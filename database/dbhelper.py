from typing import Optional


def construct_article_data(
    url: Optional[str] = None,
    title: Optional[str] = None,
    date_published: Optional[str] = None,
    text: Optional[str] = None,
    audio_file: Optional[str] = None,
    md_file: Optional[str] = None,
    vtt_file: Optional[str] = None,
    img_file: Optional[str] = None,
) -> dict:
    """
    Constructs a dictionary representing article data.

    Parameters:
    - url (Optional[str]): URL of the article.
    - title (Optional[str]): Title of the article.
    - date_published (Optional[str]): Publication date of the article.
    - text (Optional[str]): Plain text content of the article.
    - audio_file (Optional[str]): Path to an associated audio file.
    - md_file (Optional[str]): Path to an associated markdown file.
    - vtt_file (Optional[str]): Path to an associated VTT file for subtitles.
    - img_file (Optional[str]): Path to an associated image file.

    Returns:
    - dict: A dictionary containing the provided article data.
    """
    article_data = {}

    if url is not None:
        article_data["url"] = url
    if title is not None:
        article_data["title"] = title
    if date_published is not None:
        article_data["date_published"] = date_published
    if text is not None:
        article_data["plain_text"] = text
    if audio_file is not None:
        article_data["audio_file"] = audio_file
    if md_file is not None:
        article_data["markdown_file"] = md_file
    if vtt_file is not None:
        article_data["vtt_file"] = vtt_file
    if img_file is not None:
        article_data["img_file"] = img_file

    return article_data


def construct_text_data(
    title: Optional[str] = None,
    text: Optional[str] = None,
    audio_file: Optional[str] = None,
    language: Optional[str] = None,
    plain_text: Optional[str] = None,
    img_file: Optional[str] = None,
) -> dict:
    """
    Constructs a dictionary representing text data.

    Parameters:
    - title (Optional[str]): Title of the text.
    - text (Optional[str]): Content of the text.
    - audio_file (Optional[str]): Path to an associated audio file.
    - language (Optional[str]): Language of the text content.
    - plain_text (Optional[str]): Plain text version of the content.
    - img_file (Optional[str]): Path to an associated image file.

    Returns:
    - dict: A dictionary containing the provided text data.
    """
    text_data = {}

    if title is not None:
        text_data["title"] = title
    if text is not None:
        text_data["text"] = text
    if audio_file is not None:
        text_data["audio_file"] = audio_file
    if language is not None:
        text_data["language"] = language
    if plain_text is not None:
        text_data["plain_text"] = plain_text
    if img_file is not None:
        text_data["img_file"] = img_file

    return text_data
