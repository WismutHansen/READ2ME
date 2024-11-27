import os
import mimetypes
from utils.asr.audio2text import transcribe


def format_percentage(speed: float) -> str:
    """
    Converts a floating-point number to a percentage string in the form:
    1.0 -> "+0%", 1.1 -> "+10%", 0.9 -> "-10%", etc.
    Ensures the value stays between -50% and +50%.

    :param value: The floating-point value to format.
    :return: A string representing the percentage.
    """
    # Clamp the value to be between 0.5 and 1.5 (corresponding to -50% and +50%)
    clamped_value = max(0.5, min(1.5, speed))

    # Calculate the percentage change from 1.0
    percentage_change = (clamped_value - 1.0) * 100

    # Format the percentage with a "+" or "-" sign
    return f"{percentage_change:+.0f}%"


def load_transcript(voice_file: str, file_path: str) -> str:
    base_name = os.path.splitext(voice_file)[0]  # remove extension
    transcript_file = os.path.join(file_path, base_name + ".txt")

    if not os.path.exists(transcript_file):
        transcript = transcribe(os.path.join(file_path, voice_file))
        return transcript

    else:
        with open(transcript_file, "r", encoding="utf-") as file:
            transcript = file.read()
        return transcript


def get_voices_wav(directory: str) -> list:
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
