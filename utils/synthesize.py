import random
import logging
import edge_tts
from edge_tts import VoicesManager, SubMaker
from .text_extraction import extract_text
from .common_utils import get_output_files, add_mp3_tags, write_markdown_file
from llm.LLM_calls import generate_title
from .common_utils import get_mp3_duration
from database.crud import create_article

# Extracted TTS function
async def tts(text, voice, filename, vtt_file=None):
    """
    Converts text to speech and saves it as an MP3 file.
    Optionally generates a VTT subtitle file.

    Parameters:
    - text (str): The text to convert to speech.
    - voice (str): The voice identifier for the TTS engine.
    - filename (str): The path to save the MP3 file.
    - vtt_file (str, optional): The path to save the VTT subtitle file.
    """
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    submaker = SubMaker() if vtt_file else None
    with open(filename, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary" and vtt_file:
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
    # Write VTT file if subtitles are generated
    if vtt_file and submaker:
        with open(vtt_file, "w", encoding="utf-8") as file:
            file.write(submaker.generate_subs())

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

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    vtt_file = f"{base_file_name}.vtt"  # New VTT file path
    write_markdown_file(md_file, text, url)

    voices = await VoicesManager.create()
    multilingual_voices = [
        voice_info
        for voice_info in voices.voices
        if "MultilingualNeural" in voice_info["Name"] and "en-US" in voice_info["Name"]
    ]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        return None, None, None, None

    voice_name = random.choice(multilingual_voices)["Name"]

    # Use the extracted TTS function
    await tts(text, voice_name, mp3_file, vtt_file)

    add_mp3_tags(mp3_file, title, img_pth, output_dir)
    duration = get_mp3_duration(mp3_file)

    article_data = {
        "url": str(url),
        "title": str(title),
        "plain_text": str(text),
        "audio_file": str(mp3_file),
        "markdown_file": str(md_file),
        "vtt_file": str(vtt_file),
    }
    try:
        create_article(article_data)
    except Exception as e:
        logging.error(f"Could not write to database: {e}")

    logging.info(f"Successfully processed URL {url}")
    return base_file_name, mp3_file, md_file, vtt_file

async def read_text(text: str, output_dir, img_pth):
    title = generate_title(text)

    if not text:
        logging.error("No text provided")
        print("No text provided")
        return None, None, None, None

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    vtt_file = f"{base_file_name}.vtt"
    write_markdown_file(md_file, text)

    voices = await VoicesManager.create()
    multilingual_voices = [
        voice_info
        for voice_info in voices.voices
        if "MultilingualNeural" in voice_info["Name"] and "en-US" in voice_info["Name"]
    ]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        return None, None, None, None

    voice_name = random.choice(multilingual_voices)["Name"]

    # Use the extracted TTS function
    await tts(text, voice_name, mp3_file, vtt_file)

    add_mp3_tags(mp3_file, "READ2ME", img_pth, output_dir)
    logging.info("Successfully processed text")
    return base_file_name, mp3_file, md_file, vtt_file

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
