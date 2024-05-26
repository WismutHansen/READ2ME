import os
import logging
from .common_utils import get_output_files, add_mp3_tags, convert_wav_to_mp3
from .markdown_utils import write_markdown_file
from .text_extraction import extract_text
import torch
import numpy as np
from scipy.io.wavfile import write
from txtsplit import txtsplit
from tqdm import tqdm
from .styletts2.ljspeechimportable import inference

async def say_with_styletts2(url: str, output_dir: str, img_pth: str):
    try:
        text, title = extract_text(url)
        if not text or not title:
            logging.error("Failed to extract text or title")
            return None, None, None
    except Exception as e:
        logging.error(f"Failed to extract text and title from URL {url}: {e}")
        return None, None, None
    
    base_file_name, mp3_file, md_file = await get_output_files(output_dir)
    write_markdown_file(md_file, text, url)

    wav_output = f"{base_file_name}.wav"
    
    sr = 24000
    device = "cuda" if torch.cuda.is_available() else "cpu"
    noise = torch.randn(1, 1, 256).to(device)

    if not text.strip():
        logging.error("You must enter some text")
        return None, None, None
    
    if len(text) > 150000:
        logging.error("Text must be <150k characters")
        return None, None, None

    texts = txtsplit(text)
    audios = []
    for t in tqdm(texts, desc="Synthesizing"):
        audio = inference(t, noise, diffusion_steps=5, embedding_scale=1)
        if audio is not None:
            audios.append(audio)
        else:
            logging.error(f"Inference returned None for text segment: {t}")
    
    if not audios:
        logging.error("No audio segments were generated")
        return None, None, None

    full_audio = np.concatenate(audios)
    write(wav_output, sr, full_audio)

    # Convert the WAV file to MP3
    convert_wav_to_mp3(wav_output, mp3_file)

    add_mp3_tags(mp3_file, title, img_pth, output_dir)
    logging.info(f"Successfully processed URL {url}")
    return base_file_name, mp3_file, md_file

if __name__ == "__main__":
    import os
    import asyncio

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    output_dir = os.path.join(parent_dir, "Output")
    img_pth = os.path.join(parent_dir, "front.jpg")

    url = input("Enter URL to convert: ")
    asyncio.run(say_with_styletts2(url, output_dir, img_pth))