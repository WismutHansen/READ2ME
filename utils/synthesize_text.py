import edge_tts
import os
import asyncio
import markdown
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

OUTPUT_FILE = "test.mp3"
VOICE = "en-US-AndrewNeural"


async def synthesize_text(text):
    communicate = edge_tts.Communicate(text, VOICE, rate="+10%")
    progress = tqdm(total=100, desc="Synthesizing", unit="%", ncols=100)

    def update_progress(percent):
        progress.n = percent
        progress.refresh()

    await communicate.save(OUTPUT_FILE, progress_callback=update_progress)
    progress.close()


def read_markdown_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(md_content)

    # Use BeautifulSoup to strip HTML tags
    soup = BeautifulSoup(html_content, "html.parser")
    text_content = soup.get_text()

    return text_content


if __name__ == "__main__":
    markdownfile = input("Enter Markdown file path: ")
    text = read_markdown_file(markdownfile)
    print(f"Extracted text: {text}")  # Debug print to check extracted text
    if text.strip():  # Ensure there is text to synthesize
        asyncio.run(synthesize_text(text))
    else:
        print("No text found to synthesize.")
