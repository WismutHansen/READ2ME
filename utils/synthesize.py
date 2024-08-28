import random
import logging
import edge_tts
from edge_tts import VoicesManager, SubMaker
from .text_extraction import extract_text
from .common_utils import get_output_files, add_mp3_tags, write_markdown_file
from llm.LLM_calls import generate_title
from .common_utils import get_mp3_duration
from database.crud import create_article


async def synthesize_text_to_speech(url: str, output_dir, img_pth):
    try:
        text, title = await extract_text(url)
        print(title)
        if not text:
            print("Failed to extract text or title")
            raise ValueError("Failed to extract text or title")
    except Exception as e:
        logging.error(f"Failed to extract text and title from URL {url}: {e}")
        print("Failed to extract text and title from URL")
        return None, None, None, None  # Added None for VTT file

    if not text:
        logging.error(f"No text extracted from the provided URL {url}")
        print("No text extracted from the provided URL")
        return None, None, None, None  # Added None for VTT file

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    vtt_file = f"{base_file_name}.vtt"  # New VTT file path
    write_markdown_file(md_file, text, url)

    voices = await VoicesManager.create()
    multilingual_voices = [
        voice
        for voice in voices.voices
        if "MultilingualNeural" in voice["Name"] and "en-US" in voice["Name"]
    ]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        return None, None, None, None  # Added None for VTT file

    voice = random.choice(multilingual_voices)["Name"]
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    submaker = SubMaker()

    with open(mp3_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])

    # Write VTT file
    with open(vtt_file, "w", encoding="utf-8") as file:
        file.write(submaker.generate_subs())

    add_mp3_tags(mp3_file, title, img_pth, output_dir)
    duration = get_mp3_duration(mp3_file)

    article_data = {
        "url": url,
        "title": title,
        "plain_text": text,
        "audio_file": mp3_file,
        "markdown_file": md_file,
        "vtt_file": vtt_file,
    }
    try:
        create_article(article_data)
    except Exception as e:
        logging.error(f"Could not write to database: {e}")

    logging.info(f"Successfully processed URL {url}")
    return base_file_name, mp3_file, md_file, vtt_file  # Added vtt_file to return


async def read_text(text: str, output_dir, img_pth):
    title = generate_title(text)

    if not text:
        logging.error(f"No text provided")
        print("No text provided")
        return None, None, None, None  # Added None for VTT file

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    vtt_file = f"{base_file_name}.vtt"  # New VTT file path
    write_markdown_file(md_file, text)

    voices = await VoicesManager.create()
    multilingual_voices = [
        voice
        for voice in voices.voices
        if "MultilingualNeural" in voice["Name"] and "en-US" in voice["Name"]
    ]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        return None, None, None, None  # Added None for VTT file

    voice = random.choice(multilingual_voices)["Name"]
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    submaker = SubMaker()

    with open(mp3_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])

    # Write VTT file
    with open(vtt_file, "w", encoding="utf-8") as file:
        file.write(submaker.generate_subs())

    add_mp3_tags(mp3_file, "READ2ME", img_pth, output_dir)
    logging.info(f"Successfully processed text")
    return base_file_name, mp3_file, md_file, vtt_file  # Added vtt_file to return


if __name__ == "__main__":
    import os
    import asyncio

    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Go one directory up
    parent_dir = os.path.dirname(current_dir)

    # Navigate into the "Output" folder
    output_dir = os.path.join(parent_dir, "Output")

    # Image path in parent directory
    img_pth = os.path.join(parent_dir, "front.jpg")

    url = input("Enter URL to convert: ")
    asyncio.run(synthesize_text_to_speech(url, output_dir, img_pth))

