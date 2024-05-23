import random
import os
from cached_path import cached_path
from styletts2 import tts

def say_with_styletts2(text: str, filename: str, output_dir: str):
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
    out = my_tts.inference(text, target_voice_path=selected_voice, output_wav_file=output_dir+"/"+filename+".wav")
