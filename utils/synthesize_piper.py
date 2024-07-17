import random
import logging
import edge_tts
from edge_tts import VoicesManager
from .text_extraction import extract_text
from .common_utils import get_output_files, add_mp3_tags, write_markdown_file, convert_wav_to_mp3
from llm.LLM_calls import generate_title
from .piper_tts_client import PiperTTSClient
import os




async def url_with_piper(url: str, output_dir, img_pth):
    try:
        text, title = await extract_text(url)
        print(title)
        if not text:
            print("Failed to extract text or title")
            raise ValueError("Failed to extract text or title")
    except Exception as e:
        logging.error(f"Failed to extract text and title from URL {url}: {e}")
        print("Failed to extract text and title from URL")
        return None, None, None  # Instead of raising an exception, return None

    if not text:
        logging.error(f"No text extracted from the provided URL {url}")
        print("No text extracted from the provided URL")
        return None, None, None  # Instead of raising an exception, return None

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    write_markdown_file(md_file, text, url)

    wav_file = f"{base_file_name}.wav"
    script_folder = os.path.dirname(os.path.abspath(__file__))
    voice_folder = "default_female_voice/"
    parent_folder = os.path.dirname(script_folder)  # One folder up from the script folder
    output_file = os.path.join(parent_folder, wav_file)

    tts_client = PiperTTSClient(verbose=True)
    tts_client.tts(text, output_file, voice_folder)

    convert_wav_to_mp3(output_file, mp3_file)

    add_mp3_tags(mp3_file, title, img_pth, output_dir)

    # Delete the _stts2.wav file after processing
    if os.path.exists(output_file):
        os.remove(output_file)
        logging.info(f"Deleted temporary file {output_file}")

    logging.info(f"Successfully processed text with title {title}")
    return base_file_name, mp3_file, md_file


async def read_text_piper(text: str, output_dir, img_pth):
    title = generate_title(text)

    if not text:
        logging.error(f"No text provided")
        print("No text provided")
        return None, None, None  # Instead of raising an exception, return None
    
    title = generate_title(text)

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    write_markdown_file(md_file, text)

    wav_file = f"{base_file_name}.wav"
    script_folder = os.path.dirname(os.path.abspath(__file__))
    voice_folder = "default_female_voice/"
    output_file = os.path.join(script_folder, wav_file)

    tts_client = PiperTTSClient(verbose=True)
    tts_client.tts(text, output_file, voice_folder)

    convert_wav_to_mp3(output_file, mp3_file)

    add_mp3_tags(mp3_file, title, img_pth, output_dir)

    # Delete the _stts2.wav file after processing
    if os.path.exists(output_file):
        os.remove(output_file)
        logging.info(f"Deleted temporary file {output_file}")

    logging.info(f"Successfully processed text with title {title}")
    return base_file_name, mp3_file, md_file


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
    asyncio.run(url_with_piper(url, output_dir, img_pth))
