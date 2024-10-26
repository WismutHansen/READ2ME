import os
import re
import mimetypes
import random
import tempfile
import numpy as np
import soundfile as sf
import torchaudio
from cached_path import cached_path
from pydub import AudioSegment

from TTS.F5_TTS.model import DiT, UNetT
from TTS.F5_TTS.model.utils import save_spectrogram
from TTS.F5_TTS.model.utils_infer import (
    load_vocoder,
    load_model,
    preprocess_ref_audio_text,
    infer_process,
    remove_silence_for_generated_wav,
)

# Initialize vocoder
vocos = load_vocoder()

# Define model configurations
F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
E2TTS_model_cfg = dict(dim=1024, depth=24, heads=16, ff_mult=4)

# Define global variables for caching models
loaded_models = {"F5-TTS": None, "E2-TTS": None}


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
        base_name = os.path.splitext(audio_file)[0]  # Extract the filename without extension
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
        voices_to_choose_from = [voice for voice in available_voices if voice != previous_voice]
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


def load_model_on_demand(model_name):
    """Load the model only when it's needed."""
    if model_name == "F5-TTS" and not loaded_models["F5-TTS"]:
        loaded_models["F5-TTS"] = load_model(
            DiT, F5TTS_model_cfg, str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))
        )
    elif model_name == "E2-TTS" and not loaded_models["E2-TTS"]:
        loaded_models["E2-TTS"] = load_model(
            UNetT, E2TTS_model_cfg, str(cached_path("hf://SWivid/E2-TTS/E2TTS_Base/model_1200000.safetensors"))
        )
    return loaded_models[model_name]


def infer(ref_audio_orig, ref_text, gen_text, model, remove_silence, cross_fade_duration=0.15, speed=1):
    ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_orig, ref_text)

    # Load the required model
    ema_model = load_model_on_demand(model)

    final_wave, final_sample_rate, combined_spectrogram = infer_process(
        ref_audio,
        ref_text,
        gen_text,
        ema_model,
        cross_fade_duration=cross_fade_duration,
        speed=speed,
    )

    # Remove silence
    if remove_silence:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            sf.write(f.name, final_wave, final_sample_rate)
            remove_silence_for_generated_wav(f.name)
            final_wave, _ = torchaudio.load(f.name)
        final_wave = final_wave.squeeze().cpu().numpy()

    # Save the spectrogram
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_spectrogram:
        spectrogram_path = tmp_spectrogram.name
        save_spectrogram(combined_spectrogram, spectrogram_path)

    return (final_sample_rate, final_wave), spectrogram_path


def generate_podcast(script, ref_audio1, ref_text1, ref_audio2, ref_text2, model, remove_silence):
    """
    Generate a podcast from a script with two speakers.

    Args:
        script (str): The podcast script with speaker1 and speaker2 annotations
        ref_audio1 (str): Path to reference audio file for speaker1
        ref_text1 (str): Reference text for speaker1
        ref_audio2 (str): Path to reference audio file for speaker2
        ref_text2 (str): Reference text for speaker2
        model (str): Model name to use for generation
        remove_silence (bool): Whether to remove silence from generated audio

    Returns:
        str: Path to the generated podcast audio file
    """
    # Clean and normalize the script
    script = script.strip()

    # Improved regex pattern to handle various newline formats and spacing
    speaker_blocks = re.split(r"\s*(speaker[12]):[\s]*", script)

    # Remove empty strings and process blocks
    speaker_blocks = [block for block in speaker_blocks if block.strip()]

    generated_audio_segments = []

    # Process each speaker block
    for i in range(0, len(speaker_blocks), 2):
        if i + 1 >= len(speaker_blocks):
            break

        speaker = speaker_blocks[i].lower().strip()
        text = speaker_blocks[i + 1].strip()

        # Skip if text is empty
        if not text:
            continue

        # Select appropriate reference audio and text
        if speaker == "speaker1":
            ref_audio = ref_audio1
            ref_text = ref_text1
        elif speaker == "speaker2":
            ref_audio = ref_audio2
            ref_text = ref_text2
        else:
            print(f"Warning: Unknown speaker {speaker}, skipping block")
            continue

        try:
            # Generate audio for this block
            print(f"Generating audio for {speaker}: {text[:50]}...")
            audio, _ = infer(ref_audio, ref_text, text, model, remove_silence)

            # Unpack audio data
            sr, audio_data = audio

            # Save temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, sr)
                audio_segment = AudioSegment.from_wav(temp_file.name)
                os.unlink(temp_file.name)  # Clean up temp file

            # Add the audio segment
            generated_audio_segments.append(audio_segment)

            # Add a short pause between speakers (500ms)
            generated_audio_segments.append(AudioSegment.silent(duration=500))

        except Exception as e:
            print(f"Warning: Failed to generate audio for block: {e}")
            continue

    # Check if we have any generated segments
    if not generated_audio_segments:
        raise ValueError("No audio segments were generated. Please check the input script and speakers.")

    # Combine all segments
    final_podcast = generated_audio_segments[0]
    for segment in generated_audio_segments[1:]:
        final_podcast += segment

    # Export final podcast
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        podcast_path = temp_file.name
        final_podcast.export(podcast_path, format="wav")

    return podcast_path


def parse_speechtypes_text(gen_text):
    # Pattern to find (Emotion)
    pattern = r"\((.*?)\)"

    # Split the text by the pattern
    tokens = re.split(pattern, gen_text)

    segments = []

    current_emotion = "Regular"

    for i in range(len(tokens)):
        if i % 2 == 0:
            # This is text
            text = tokens[i].strip()
            if text:
                segments.append({"emotion": current_emotion, "text": text})
        else:
            # This is emotion
            emotion = tokens[i].strip()
            current_emotion = emotion

    return segments


def test_podcast_generation():
    """Test function to verify podcast generation"""
    test_script = """
    speaker1: Hello, this is a test of the podcast generation system.
    speaker2: Yes, we're testing if the audio generation works properly.
    speaker1: Let's make sure all the timing and transitions are smooth.
    """

    # Load models and voices
    model = "F5-TTS"
    voice_path = "utils/voices/"
    voices = get_available_voices(voice_path)

    if not voices:
        raise ValueError("No voice files found in the voices directory")

    # Select voices
    voice_1 = voices[0]  # Use first voice for testing
    voice_2 = voices[1] if len(voices) > 1 else voices[0]  # Use second voice or first if only one available

    # Load reference texts
    ref_text_1 = load_transcript(voice_1, voice_path)
    ref_text_2 = load_transcript(voice_2, voice_path)

    # Generate paths
    abs_voice_path_1 = os.path.join(voice_path, voice_1)
    abs_voice_path_2 = os.path.join(voice_path, voice_2)

    # Generate podcast
    try:
        podcast_path = generate_podcast(
            test_script, abs_voice_path_1, ref_text_1, abs_voice_path_2, ref_text_2, model, False
        )
        print(f"Test successful! Podcast generated at: {podcast_path}")
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False


if __name__ == "__main__":
    test_podcast_generation()
