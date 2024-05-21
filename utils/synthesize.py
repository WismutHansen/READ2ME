import os
import random
import logging
import edge_tts
from edge_tts import VoicesManager
from .text_extraction import extract_text
from .file_utils import get_output_files, add_mp3_tags

async def synthesize_text_to_speech(url: str, output_dir, img_pth):
    try:
        text, title = extract_text(url)
        if not text or not title:
            raise ValueError("Failed to extract text or title")
    except Exception as e:
        logging.error(f"Failed to extract text and title from URL {url}: {e}")
        return None, None  # Instead of raising an exception, return None
    
    if not text:
        logging.error(f"No text extracted from the provided URL {url}")
        return None, None  # Instead of raising an exception, return None

    base_file_name, mp3_file, md_file = await get_output_files(output_dir)

    with open(md_file, 'w') as md_file_handle:
        md_file_handle.write(text)
        md_file_handle.write(f"\n\nSource: {url}")

    voices = await VoicesManager.create()
    multilingual_voices = [voice for voice in voices.voices if "MultilingualNeural" in voice["Name"]]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        return None, None  # Instead of raising an exception, return None
    
    voice = random.choice(multilingual_voices)["Name"]
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(mp3_file)
    add_mp3_tags(mp3_file, title, img_pth, output_dir)
    logging.info(f"Successfully processed URL {url}")
    return mp3_file, md_file
