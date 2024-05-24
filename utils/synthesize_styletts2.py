import random
import os
from .common_utils import get_output_files, add_mp3_tags, convert_wav_to_mp3
from .markdown_utils import write_markdown_file
from cached_path import cached_path
from styletts2 import tts
from .text_extraction import extract_text
import logging

def say_with_styletts2(text_or_url: str, filename: str, output_dir: str):
    # List of available voices
    voices = [
        "voices/Female_en-US_Aria_Neural.mp3",
        "voices/Female_en-US_Ava_Neural.mp3",
        "voices/Female_en-US_Emma_Neural.mp3",
        "voices/Female_en-US_Jenny_Neural.mp3",
        "voices/Female_en-US_Michelle_Neural.mp3",
        "voices/Male_en-US_Andrew_Neural.mp3",
        "voices/Male_en-US_Brian_Neural.mp3",
        "voices/Male_en-US_Guy_Neural.mp3",
        "voices/Male_en-US_Roger_Neural.mp3",
        "voices/Male_en-US_Steffan_Neural.mp3"
    ]

    # Determine if input is URL or text
    if text_or_url.startswith('http'):
        # Extract text from URL
        text, title = extract_text(text_or_url)
        if not text:
            logging.error(f"Failed to extract text from URL: {text_or_url}")
            return None, None, None
    else:
        text = text_or_url
        title = text[:50]

    # Randomly select a voice from the list
    selected_voice = random.choice(voices)

    # Define the cache directory
    cache_dir = "./Utils/Models/StyleTTS2-LibriTTS"
    os.makedirs(cache_dir, exist_ok=True)

    # Download and cache the required files
    model_checkpoint_path = cached_path("hf://yl4579/StyleTTS2-LibriTTS/Models/LibriTTS/epochs_2nd_00020.pth", cache_dir=cache_dir)
    config_path = cached_path("hf://yl4579/StyleTTS2-LibriTTS/Models/LibriTTS/config.yml", cache_dir=cache_dir)
    
    # Initialize the StyleTTS2 model with the downloaded files
    my_tts = tts.StyleTTS2(model_checkpoint_path=model_checkpoint_path, config_path=config_path)

    # Perform inference with the randomly selected voice
    wav_output = os.path.join(output_dir, f"{filename}.wav")
    my_tts.inference(text, target_voice_path=selected_voice, output_wav_file=wav_output)

    # Convert the WAV file to MP3
    mp3_output = os.path.join(output_dir, f"{filename}.mp3")
    convert_wav_to_mp3(wav_output, mp3_output)

    # Write markdown file
    md_file = f"{output_dir}/{filename}.md"
    write_markdown_file(md_file, text, text_or_url if text_or_url.startswith('http') else None)

    # Add MP3 tags
    add_mp3_tags(mp3_output, title, img_pth, output_dir)

    logging.info(f"Successfully processed {'URL' if text_or_url.startswith('http') else 'text'}: {text_or_url}")
    return filename, mp3_output, md_file