import os
import logging
from .common_utils import (
    get_output_files,
    add_mp3_tags,
    convert_wav_to_mp3,
    write_markdown_file,
)
from .text_extraction import extract_text
import torch
import numpy as np
from scipy.io.wavfile import write
from txtsplit import txtsplit
from tqdm import tqdm
from .styletts2.ljspeechimportable import inference
import glob
from .voiceconv import voice2voice


async def extract_text_from_url(url: str):
    try:
        text, title = await extract_text(url)
        if not text or not title:
            logging.error("Failed to extract text or title")
            return None, None
    except Exception as e:
        logging.error(f"Failed to extract text and title from URL {url}: {e}")
        return None, None
    return text, title


async def text_to_speech_with_styletts2(
    text: str, title: str, output_dir: str, img_pth: str
):
    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    write_markdown_file(md_file, text, title)

    wav_output = f"{base_file_name}_stts2.wav"

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

    #    # Check if there is a checkpoint with .pth ending in .utils/rvc/Models
    #    checkpoint_path = "./utils/rvc/Models/Male_1.pth"
    #    if os.path.isfile(checkpoint_path):
    #        # Using RVC to change the voice:
    #
    #        backend = "cpu"
    #        if torch.cuda.is_available():
    #            backend = "cuda:0"
    #
    #        infer_file(
    #            input_path=wav_output,
    #            model_path=checkpoint_path,
    #            index_path="./utils/rvc/Models/Male_1.index",  # Optional: specify path to index file if available
    #            device=backend, # Use cpu or cuda
    #            f0method="rmvpe",  # Choose between 'harvest', 'crepe', 'rmvpe', 'pm'
    #            f0up_key=-9,  # Transpose setting
    #            opt_path=f"{base_file_name}_rvc.wav", # Output file path
    #            index_rate=0.5,
    #            filter_radius=3,
    #            resample_sr=0,  # Set to desired sample rate or 0 for no resampling.
    #            rms_mix_rate=0.25,
    #            protect=0.33,
    #            version="v2"
    #        )
    #
    #        rvc_file = f"{base_file_name}_rvc.wav"
    #        convert_wav_to_mp3(rvc_file, mp3_file)
    #
    #    else:
    #        convert_wav_to_mp3(wav_output, mp3_file)

    convert_wav_to_mp3(wav_output, mp3_file)

    add_mp3_tags(mp3_file, title, img_pth, output_dir)

    # Delete the _stts2.wav file after processing
    if os.path.exists(wav_output):
        os.remove(wav_output)
        logging.info(f"Deleted temporary file {wav_output}")

    logging.info(f"Successfully processed text with title {title}")
    return base_file_name, mp3_file, md_file


async def say_with_styletts2(url: str, output_dir: str, img_pth: str):
    text, title = await extract_text_from_url(url)
    if not text or not title:
        return None, None, None
    return await text_to_speech_with_styletts2(text, title, output_dir, img_pth)


if __name__ == "__main__":
    import os
    import asyncio

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    output_dir = os.path.join(parent_dir, "Output")
    img_pth = os.path.join(parent_dir, "front.jpg")

    url = input("Enter URL to convert: ")
    asyncio.run(say_with_styletts2(url, output_dir, img_pth))
