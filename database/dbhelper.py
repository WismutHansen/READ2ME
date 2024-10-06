def construct_article_data(
    url=None, title=None, text=None, mp3_file=None, md_file=None, vtt_file=None
):
    article_data = {}

    if url is not None:
        article_data["url"] = url
    if title is not None:
        article_data["title"] = title
    if date_published is not None:
        article_data["date_published"] = date_published
    if text is not None:
        article_data["plain_text"] = text
    if mp3_file is not None:
        article_data["audio_file"] = mp3_file
    if md_file is not None:
        article_data["markdown_file"] = md_file
    if vtt_file is not None:
        article_data["vtt_file"] = vtt_file

    return article_data

