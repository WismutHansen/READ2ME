#!/usr/bin/env python3
# text2speech.py
# -*- coding: utf-8 -*-

import json
import os
import argparse
import random
import string

import numpy as np
import soundfile as sf  # Alias for clarity
import torch

from . import inference
from txtsplit import txtsplit  # Import txtsplit
from typing import Optional, Tuple, List
from .text_utils import segment_and_tokenize

VOICES_JSON_PATH = (
    "TTS/styletts2_studio/voices.json"  # Contains your known style vectors
)
RANDOM_VOICES_JSON_PATH = (
    "TTS/styletts2_studio/random_voices.json"  # We'll store newly sampled vectors here
)

##############################################################################
# DEVICE CONFIGURATION
##############################################################################
# Detect if CUDA is available and set the device accordingly
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")


def generate_long_form_tts(full_text: str, voice: str, speed: float = 1.2):
    """
    Generate TTS for a large `full_text`, splitting it into smaller segments
    and concatenating the resulting audio.

    Returns: (np.float32 array) final_audio
    """
    # 1. Segment the text
    segments = segment_and_tokenize(full_text)
    # segments is a list of (seg_text, seg_phonemes)

    # 2. For each segment, call `generate_tts(...)`
    audio_chunks = []
    for i, (seg_text, seg_ps) in enumerate(segments, 1):
        print(f"[LongForm] Generating chunk {i}/{len(segments)}: {seg_text[:40]}...")
        audio = tts_normal(text=full_text, voice=voice, speed=speed)
        if audio is not None:
            audio_chunks.append(audio)
        else:
            print(f"[LongForm] Skipped empty segment {i}...")

    if not audio_chunks:
        return None

    # 3. Concatenate the audio
    final_audio = np.concatenate(audio_chunks, axis=0)
    return final_audio


##############################################################################
# JSON LOAD/SAVE
##############################################################################
def load_json(path: str) -> dict:
    """
    Load existing style vectors from the given JSON file.

    Additionally, validates that all style vectors have the same length.

    Args:
        path (str): Path to the JSON file.

    Returns:
        dict: Loaded JSON data.
    """
    data = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        # Verify all vectors have the same length
        lengths = set(len(vec) for vec in data.values())
        if len(lengths) > 1:
            raise ValueError(
                f"Inconsistent vector lengths found in '{path}': {lengths}. "
                "All style vectors must have the same dimensionality."
            )
        print(f"Loaded {len(data)} style vectors from '{path}'.")
    else:
        print(f"No existing '{path}' found. Starting with an empty dictionary.")
    return data


def save_json(data: dict, path: str) -> None:
    """
    Save a dict of style vectors to the given JSON file.

    Args:
        data (dict): Data to save.
        path (str): Path to the JSON file.
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} style vectors to '{path}'.")


##############################################################################
# GAUSSIAN FIT AND SAMPLING
##############################################################################


def fit_gaussian_to_voices(voices_data: dict) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit a Gaussian distribution (mean & cov) to the style vectors in 'voices_data'.
    'voices_data' is a dict: { "key.wav": <list-of-floats>, ... }

    Args:
        voices_data (dict): Dictionary containing style vectors.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Mean and covariance of the fitted Gaussian.
    """
    all_vecs = []

    for key, data in voices_data.items():
        # Convert to array
        arr = np.array(data, dtype=np.float32)
        # Squeeze out any dimension of size 1
        arr = np.squeeze(arr)

        if arr.ndim == 1:
            # It's shape (D,)
            all_vecs.append(arr)
        else:
            # If still not 1D, we skip or warn
            print(
                f"Skipping '{key}' because shape is {arr.shape}, not 1D after squeeze."
            )

    # Must have at least 2 valid vectors to compute a meaningful covariance
    if len(all_vecs) < 2:
        raise ValueError(
            "Need at least 2 valid style vectors to fit a Gaussian distribution.\n"
            "Check that each entry is 1D (or (1,D) which can be squeezed)."
        )

    # Stack into (N, D)
    mat = np.stack(all_vecs, axis=0)  # shape => (N, D)
    # Sanity check
    if mat.ndim != 2:
        raise ValueError("Style vectors must collectively form a 2D array (N, D).")

    # Compute mean & covariance
    mean = np.mean(mat, axis=0)  # shape (D,)
    cov = np.cov(mat, rowvar=False)  # shape (D, D)
    print("Fitted Gaussian distribution to style vectors.")
    return mean, cov


def sample_random_style(mean: np.ndarray, cov: np.ndarray) -> torch.Tensor:
    """
    Sample a random style vector from a Gaussian distribution.

    Args:
        mean (np.ndarray): Mean vector of the Gaussian.
        cov (np.ndarray): Covariance matrix of the Gaussian.

    Returns:
        torch.Tensor: Sampled style vector as a tensor of shape (1, D).
    """
    # Sample from multivariate normal distribution
    z = np.random.multivariate_normal(mean, cov)
    # Convert to torch tensor
    style_tensor = torch.tensor(z, dtype=torch.float32).to(device)  # Move to device
    # Unsqueeze to shape (1, D)
    style_tensor = style_tensor.unsqueeze(0)
    print(f"Sampled a new random style vector with shape {style_tensor.shape}.")
    return style_tensor


##############################################################################
# UTILITIES
##############################################################################


def parse_speed(value) -> float:
    """
    Convert 'value' into a float between 0.5 and 2.0 based on custom logic.

    Examples:
        parse_speed("120%") -> 1.2
        parse_speed(0.3)    -> 0.5 (clamped)
        parse_speed(5)      -> 2.0 (clamped)
        parse_speed("100%") -> 1.0
        parse_speed(1)      -> 1.0
        parse_speed(3)      -> 2.0 (clamped)
        parse_speed(50)     -> 0.5
        parse_speed(100)    -> 1.0
        parse_speed(130)    -> 1.3
        parse_speed("150")  -> 1.5
    """

    # 1) If string ends with '%', parse percentage
    if isinstance(value, str):
        value = value.strip()
        if value.endswith("%"):
            numeric_str = value[:-1].strip()  # remove '%' suffix
            try:
                f = float(numeric_str)
            except ValueError:
                print(
                    f"Invalid speed format '{value}'. Falling back to default speed 1.0."
                )
                f = 100.0  # fallback to "100%" -> 1.0
            speed = f / 100.0
        else:
            # It's a normal string; parse as float
            try:
                f = float(value)
            except ValueError:
                print(
                    f"Invalid speed format '{value}'. Falling back to default speed 1.0."
                )
                f = 100.0  # fallback to "100" -> 1.0
            # If f >= 10, treat as f/100. Example: 50 -> 0.5, 150 -> 1.5
            speed = f / 100.0 if f >= 10 else f
    else:
        # 2) If not string, parse as float
        try:
            f = float(value)
        except ValueError:
            print(f"Invalid speed value '{value}'. Falling back to default speed 1.0.")
            f = 1.0  # fallback to 1.0
        # If f >= 10, treat as f/100
        speed = f / 100.0 if f >= 10 else f

    # 3) Clamp to [0.5, 2.0]
    clamped_speed = max(0.5, min(2.0, speed))
    if clamped_speed != speed:
        print(f"Speed {speed} clamped to {clamped_speed}.")
    else:
        print(f"Parsed speed: {clamped_speed}")
    return clamped_speed


def concatenate_audios(audios: List[np.ndarray]) -> np.ndarray:
    """
    Concatenate a list of NumPy audio arrays into a single array.

    Args:
        audios (List[np.ndarray]): List of audio waveforms to concatenate.

    Returns:
        np.ndarray: Concatenated audio waveform.
    """
    return np.concatenate(audios, axis=0)


##############################################################################
# SYNTHESIS CORE FUNCTION
##############################################################################
def synthesize_audio(
    text_chunks: List[str],
    style_vec: torch.Tensor,
    speed: float,
    alpha: float = 0.3,
    beta: float = 0.7,
    diffusion_steps: int = 7,
    embedding_scale: float = 1.0,
) -> Optional[np.ndarray]:
    """
    Core function to synthesize audio from text chunks and a style vector.

    Args:
        text_chunks (List[str]): List of text segments to synthesize.
        style_vec (torch.Tensor): Style vector tensor of shape (1, D).
        speed (float): Parsed speed factor.
        alpha (float): Alpha parameter for inference.
        beta (float): Beta parameter for inference.
        diffusion_steps (int): Number of diffusion steps for inference.
        embedding_scale (float): Embedding scale parameter.

    Returns:
        Optional[np.ndarray]: Concatenated audio waveform, or None if synthesis fails.
    """
    audios = []
    for idx, chunk in enumerate(text_chunks, 1):
        print(f"Synthesizing chunk {idx}/{len(text_chunks)}...")
        audio_segment = inference.inference(
            chunk,
            style_vec,
            alpha=alpha,
            beta=beta,
            diffusion_steps=diffusion_steps,
            embedding_scale=embedding_scale,
            speed=speed,
        )
        if audio_segment is not None:
            audios.append(audio_segment)
            print(f"Chunk {idx} synthesized successfully.")
        else:
            print(f"Inference returned None for text segment {idx}: {chunk[:30]}...")

    if not audios:
        print("No audio segments were generated.")
        return None

    # Concatenate all audio segments
    print("Concatenating audio segments...")
    full_audio = concatenate_audios(audios)
    print(f"Concatenated audio length: {len(full_audio)} samples.")
    return full_audio


##############################################################################
# TTS USING A RANDOMLY SAMPLED STYLE
##############################################################################
def tts_randomized(
    text: str, speed: float = 1.2
) -> Tuple[Optional[np.ndarray], Optional[torch.Tensor]]:
    """
    1) Loads style vectors from voices.json
    2) Fits a Gaussian to those vectors
    3) Samples a new style vector from that distribution
    4) Saves it in random_voices.json
    5) Synthesizes TTS using that random style, handling long texts.

    Args:
        text (str): The text to be synthesized.
        speed (float): Speed of the generated audio.

    Returns:
        Tuple[Optional[np.ndarray], Optional[torch.Tensor]]: (audio_waveform, style_vector)
    """
    # Load known style vectors from voices.json
    voices_data = load_json(VOICES_JSON_PATH)
    if not voices_data:
        print(f"No data found in '{VOICES_JSON_PATH}'; cannot sample a random style.")
        return None, None

    # Fit Gaussian
    try:
        mean, cov = fit_gaussian_to_voices(voices_data)
    except ValueError as e:
        print(f"Error fitting Gaussian: {e}")
        return None, None

    # Sample new vector
    random_style_tensor = sample_random_style(mean, cov)

    # Optionally create a random key for storing
    random_key = "random_" + "".join(random.choices(string.digits, k=6))
    print(f"Generated random style key: '{random_key}'")

    # Save in random_voices.json
    random_voices_data = load_json(RANDOM_VOICES_JSON_PATH)
    random_voices_data[random_key] = random_style_tensor.squeeze(0).tolist()
    save_json(random_voices_data, RANDOM_VOICES_JSON_PATH)
    print(
        f"Saved random style vector to '{RANDOM_VOICES_JSON_PATH}' under key '{random_key}'."
    )

    # Parse speed
    speed = parse_speed(speed)

    # Split text into manageable chunks using txtsplit
    print("Splitting text into chunks...")
    text_chunks = txtsplit(text)
    print(f"Text split into {len(text_chunks)} chunks.")

    # Synthesize audio using the core function
    full_audio = synthesize_audio(
        text_chunks=text_chunks, style_vec=random_style_tensor, speed=speed
    )

    return full_audio, random_style_tensor


##############################################################################
# NORMAL (NON-RANDOM) TTS LOGIC
##############################################################################
def get_or_compute_style_vector(key_or_path: str, voices_data: dict) -> torch.Tensor:
    """
    If key_or_path is in voices_data, load it.
    If it's a file path, compute style from audio.
    Otherwise, raise an error.

    Args:
        key_or_path (str): Voice key or file path.
        voices_data (dict): Dictionary of existing style vectors.

    Returns:
        torch.Tensor: Style vector tensor of shape (1, D).
    """
    if key_or_path in voices_data:
        print(f"Found style vector for '{key_or_path}' in '{VOICES_JSON_PATH}'.")
        style_vec = torch.tensor(voices_data[key_or_path], dtype=torch.float32).to(
            device
        )  # Move to device
    elif os.path.isfile(key_or_path):
        print(
            f"No existing style for '{key_or_path}'. Attempting to compute from audio..."
        )
        style_vec = inference.compute_style(key_or_path)
        if style_vec is None:
            raise ValueError(f"Failed to compute style vector from '{key_or_path}'.")
        style_vec = style_vec.to(device)  # Move to device
        voices_data[key_or_path] = style_vec.squeeze(0).tolist()
        save_json(voices_data, VOICES_JSON_PATH)
        print(
            f"Computed and saved new style vector for '{key_or_path}' to '{VOICES_JSON_PATH}'."
        )
    else:
        raise ValueError(
            f"'{key_or_path}' not found in '{VOICES_JSON_PATH}' and is not a valid file path."
        )

    print(f"Original style vector shape: {style_vec.shape}")

    # Ensure style_vec is 2D: (1, D)
    if style_vec.dim() == 1:
        style_vec = style_vec.unsqueeze(0)
        style_vec = style_vec.to(device)  # Ensure it's on the correct device
        print(f"Unsqueezed style vector to shape: {style_vec.shape}")
    elif style_vec.dim() == 3:
        style_vec = style_vec.squeeze(1).to(device)
        print(f"Squeezed style vector to shape: {style_vec.shape}")
    elif style_vec.dim() != 2:
        raise ValueError(
            f"Unexpected style vector dimensions: {style_vec.shape}. Expected 2D tensor."
        )

    print(f"Processed style vector shape: {style_vec.shape}")
    return style_vec


def validate_style_vectors(voices_data: dict):
    """
    Validates that all style vectors in voices_data have the same dimensionality.

    Args:
        voices_data (dict): Dictionary containing style vectors.

    Raises:
        ValueError: If inconsistent vector lengths are found.
    """
    if not voices_data:
        print("No style vectors to validate.")
        return

    lengths = set(len(vec) for vec in voices_data.values())
    if len(lengths) > 1:
        raise ValueError(
            f"Inconsistent style vector lengths found: {lengths}. "
            "All style vectors must have the same dimensionality."
        )
    print("All style vectors have consistent lengths.")


def tts_normal(text: str, voice: str, speed: float = 1.2) -> Optional[np.ndarray]:
    """
    Load an existing style vector from voices.json if it exists and has 'voice'.
    Otherwise, if 'voice' is a valid .wav file, compute its style vector
    and store it. Finally, run normal TTS with the obtained style vector,
    handling long texts.

    Args:
        text (str): The text to be synthesized.
        voice (str): Either the key in voices.json or a .wav file path.
        speed (float): Speed of the generated audio.

    Returns:
        Optional[np.ndarray]: Synthesized audio waveform, or None if something fails.
    """
    # Load voices_data
    try:
        voices_data = load_json(VOICES_JSON_PATH)
        validate_style_vectors(voices_data)
    except ValueError as e:
        print(f"Error loading/validating '{VOICES_JSON_PATH}': {e}")
        return None

    try:
        style_vec = get_or_compute_style_vector(voice, voices_data)
    except ValueError as e:
        print(e)
        return None

    if style_vec is None:
        print("No style vector found or computed; cannot run TTS.")
        return None

    # Parse speed
    speed = parse_speed(speed)

    # Split text into manageable chunks using txtsplit
    print("Splitting text into chunks...")
    text_chunks = txtsplit(text)
    print(f"Text split into {len(text_chunks)} chunks.")

    # Synthesize audio using the core function
    full_audio = synthesize_audio(
        text_chunks=text_chunks,
        style_vec=style_vec,
        speed=speed,
    )

    return full_audio


##############################################################################
# TTS USING A DIRECTLY PROVIDED STYLE VECTOR
##############################################################################
def tts_with_style_vector(
    text: str,
    style_vec: torch.Tensor,
    speed: float = 1.2,
    alpha: float = 0.3,
    beta: float = 0.7,
    diffusion_steps: int = 7,
    embedding_scale: float = 1.0,
) -> Optional[np.ndarray]:
    """
    Perform TTS synthesis using a *directly provided* style vector.

    Args:
        text (str): The text to be spoken.
        style_vec (torch.Tensor): A PyTorch tensor representing the style vector.
                                  Should be shape (1, D) if the pipeline expects a batch dimension.
        speed (float): Speed factor for TTS. (Use parse_speed to handle fancy inputs.)
        alpha (float): Weight for alpha in your inference function.
        beta (float): Weight for beta in your inference function.
        diffusion_steps (int): Number of diffusion steps for your TTS pipeline.
        embedding_scale (float): Classifier-free guidance scale or similar.

    Returns:
        Optional[np.ndarray]: Synthesized audio waveform as a NumPy array (float32), or None if synthesis fails.
    """
    # Ensure style_vec has shape (1, D)
    if style_vec.dim() == 1:
        style_vec = style_vec.unsqueeze(0)  # e.g. (D,) -> (1, D)
        style_vec = style_vec.to(device)  # Move to device
        print(f"Unsqueezed style vector to shape: {style_vec.shape}")
    elif style_vec.dim() == 3:
        style_vec = style_vec.squeeze(1).to(device)
        print(f"Squeezed style vector to shape: {style_vec.shape}")
    elif style_vec.dim() != 2:
        print(f"Unexpected style vector shape: {style_vec.shape}. Expected 2D tensor.")
        return None

    print(f"Style vector shape for synthesis: {style_vec.shape}")

    # Parse speed
    speed_val = parse_speed(speed)

    # Split text into manageable chunks using txtsplit
    print("Splitting text into chunks...")
    text_chunks = txtsplit(text)
    print(f"Text split into {len(text_chunks)} chunks.")

    # Synthesize audio using the core function
    full_audio = synthesize_audio(
        text_chunks=text_chunks,
        style_vec=style_vec,
        speed=speed_val,
        alpha=alpha,
        beta=beta,
        diffusion_steps=diffusion_steps,
        embedding_scale=embedding_scale,
    )

    return full_audio


##############################################################################
# MAIN CLI
##############################################################################
def main():
    parser = argparse.ArgumentParser(
        description="Script to TTS with either random style sampling or normal style usage."
    )
    parser.add_argument(
        "--text",
        type=str,
        default="Hello from a random style or normal style TTS script!",
        help="Text to be spoken.",
    )
    parser.add_argument(
        "--speed",
        type=str,  # Changed to str to handle inputs like "120%"
        default="1.2",
        help="Speed of the generated audio (e.g., '120%', '1.2').",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="If not using --randomize, specify a voice key or .wav path to load/compute style.",
    )
    parser.add_argument(
        "--randomize",
        action="store_true",
        help="Use random style sampling from a fitted Gaussian of known styles.",
    )
    parser.add_argument(
        "--output", type=str, default="output.wav", help="Output WAV file name."
    )
    args = parser.parse_args()

    if args.randomize:
        # Approach: random style from distribution
        print("Sampling a new random style vector from 'voices.json' distribution...")
        audio, _ = tts_randomized(text=args.text, speed=args.speed)
    else:
        # Normal approach: use a style key or fallback
        print("Using normal style approach (loading or computing from 'voices.json').")
        if args.voice is None:
            print("Error: --voice must be specified when not using --randomize.")
            parser.print_help()
            return
        audio = tts_normal(text=args.text, voice=args.voice, speed=args.speed)

    if audio is not None:
        # Ensure audio is a NumPy array of type float32
        if not isinstance(audio, np.ndarray):
            print("Error: Synthesized audio is not a NumPy array.")
            return
        if audio.dtype != np.float32:
            print(f"Converting audio from {audio.dtype} to float32.")
            audio = audio.astype(np.float32)

        # Save the concatenated audio
        try:
            sf.write(args.output, audio, 24000)
            print(f"Audio saved to '{args.output}'.")
        except Exception as e:
            print(f"Failed to save audio to '{args.output}': {e}")
    else:
        print("No audio was generated. Check logs above for errors.")


if __name__ == "__main__":
    main()
