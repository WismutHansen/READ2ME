import os


def write_markdown_file(md_file_path, text, url=None):
    with open(md_file_path, "w") as md_file_handle:
        md_file_handle.write(text)
        if url:
            md_file_handle.write(f"\n\nSource: {url}")