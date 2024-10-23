import os
import sys
import torch
import numpy as np
import random
import tomli
import mimetypes
import importlib.util
from vocos import Vocos
from pydub import AudioSegment

# Add F5 submodule to be used as a module
# Get the absolute path of the F5_TTS folder
submodule_path = os.path.join(os.path.dirname(__file__), "F5_TTS")
toml_path = os.path.join(submodule_path, "inference-cli.toml")

# Load the TOML file using the dynamically constructed path
with open(toml_path, "rb") as f:
    config = tomli.load(f)
# Add the submodule path to sys.path
sys.path.append(submodule_path)

# Load the module dynamically
module_name = "inference-cli"
module_path = os.path.join(submodule_path, "inference-cli.py")

spec = importlib.util.spec_from_file_location(module_name, module_path)
inference_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inference_cli)

# Now you can access the functions from inference-cli.py
main_process = inference_cli.main_process

device = (
    "cuda"
    if torch.cuda.is_available()
    else "mps"
    if torch.backends.mps.is_available()
    else "cpu"
)

vocos = Vocos.from_pretrained("charactr/vocos-mel-24khz")

print(f"Using {device} device")


# --------------------- Settings -------------------- #


def get_available_voices(directory: str) -> list:
    """
    Scans the given directory for available voices by matching audio and .txt files.

    Args:
        directory (str): Path to the directory containing audio and .txt files.

    Returns:
        list: A list of available voice filenames (including their extensions).
    """
    available_voices = []

    # Get list of all audio and .txt files in the directory
    audio_files = {
        f
        for f in os.listdir(directory)
        if mimetypes.guess_type(f)[0] and mimetypes.guess_type(f)[0].startswith("audio")
    }
    transcript_files = {f for f in os.listdir(directory) if f.endswith(".txt")}

    # Find common base filenames (without extensions) that have both audio and .txt files
    for audio_file in audio_files:
        base_name = os.path.splitext(audio_file)[
            0
        ]  # Extract the filename without extension
        transcript_file = base_name + ".txt"
        if transcript_file in transcript_files:
            available_voices.append(audio_file)  # Append the full audio filename

    return available_voices


def pick_random_voice(available_voices: list, previous_voice: str = None) -> str:
    """
    Picks a random voice from the list of available voices, ensuring it is different from the previously picked voice.

    Args:
        available_voices (list): A list of available voice names.
        previous_voice (str, optional): The voice that was previously picked, if any.

    Returns:
        str: The randomly picked voice.
    """
    if not available_voices:
        raise ValueError("No available voices to select from.")

    if previous_voice and previous_voice in available_voices:
        # Filter out the previous voice from the available choices
        voices_to_choose_from = [
            voice for voice in available_voices if voice != previous_voice
        ]
    else:
        voices_to_choose_from = available_voices

    if not voices_to_choose_from:
        raise ValueError("Only one voice available, cannot pick a different one.")

    # Pick a random voice from the remaining choices
    return random.choice(voices_to_choose_from)


def load_transcript(voice_file: str, file_path: str) -> str:
    base_name = os.path.splitext(voice_file)[0]  # remove extension
    transcript_file = os.path.join(file_path, base_name + ".txt")

    if not os.path.exists(transcript_file):
        transcript = transcribe_audio(os.path.join(file_path, voice_file))
        return transcript

    else:
        with open(transcript_file, "r", encoding="utf-") as file:
            transcript = file.read()
        return transcript


def save_to_mp3(output: tuple, output_path: str):
    """
    Saves the generated audio from `infer` function to an MP3 file.

    Args:
        output (tuple): A tuple with target sample rate and the generated audio data (from infer function).
        output_path (str): The file path where the MP3 file will be saved.

    Returns:
        None
    """

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    target_sample_rate, combined_audio = output

    # Convert the numpy array to an AudioSegment
    audio_segment = AudioSegment(
        data=np.int16(combined_audio * 32767).tobytes(),  # convert to 16-bit PCM
        sample_width=2,  # 2 bytes per sample (16-bit)
        frame_rate=target_sample_rate,
        channels=1,  # Assuming mono audio, change to 2 for stereo
    )

    # Export to MP3
    audio_segment.export(output_path + "/audio.mp3", format="mp3")
    print(f"Audio saved to {output_path}")


# ---------------------------------------------------------------------------------------------#

if __name__ == "__main__":
    voice_path = "utils/voices/"
    text = input("Please enter some text: ")
    voices = get_available_voices(voice_path)
    voice_file = pick_random_voice(voices)
    transcript = load_transcript(voice_file, voice_path)
    abs_voice_path = os.path.join(voice_path, voice_file)
    audio = main_process(abs_voice_path, transcript, text, "F5-TTS", false)
    # audio = F5_text_to_speech(abs_voice_path, transcript, text, "output.wav")
