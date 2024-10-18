import os
import re
import torch
import torchaudio
import numpy as np
import tempfile
import random
import mimetypes
import gc
import tqdm
import soundfile as sf
from pathlib import Path
from pydub import AudioSegment, silence
from einops import rearrange
from vocos import Vocos
from pydub import AudioSegment
from cached_path import cached_path
from transformers import pipeline
from model import CFM, DiT
from model.utils import (
    get_tokenizer,
    load_checkpoint,
    convert_char_to_pinyin,
)

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

target_sample_rate = 24000
n_mel_channels = 100
hop_length = 256
target_rms = 0.1
nfe_step = 32  # 16, 32
cfg_strength = 2.0
ode_method = "euler"
sway_sampling_coef = -1.0
speed = 1.0
# fix_duration = 27  # None or float (duration in seconds)
fix_duration = None


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


def load_model(repo_name, exp_name, model_cls, model_cfg, ckpt_step):
    ckpt_path = str(
        cached_path(f"hf://SWivid/{repo_name}/{exp_name}/model_{ckpt_step}.safetensors")
    )
    vocab_char_map, vocab_size = get_tokenizer("Emilia_ZH_EN", "pinyin")
    model = CFM(
        transformer=model_cls(
            **model_cfg, text_num_embeds=vocab_size, mel_dim=n_mel_channels
        ),
        mel_spec_kwargs=dict(
            target_sample_rate=target_sample_rate,
            n_mel_channels=n_mel_channels,
            hop_length=hop_length,
        ),
        odeint_kwargs=dict(
            method=ode_method,
        ),
        vocab_char_map=vocab_char_map,
    ).to(device)

    model = load_checkpoint(model, ckpt_path, device, use_ema=True)

    return model


# load models
F5TTS_model_cfg = dict(
    dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4
)


def chunk_text(text, max_chars=200):
    """
    Splits the input text into chunks, each with a maximum number of characters.
    Args:
        text (str): The text to be split.
        max_chars (int): The maximum number of characters per chunk.
    Returns:
        List[str]: A list of text chunks.
    """
    chunks = []
    current_chunk = ""
    # Split the text into sentences based on punctuation followed by whitespace
    sentences = re.split(r"(?<=[;:.!?])\s+|(?<=[；：，。！？])", text)

    for sentence in sentences:
        if (
            len(current_chunk.encode("utf-8")) + len(sentence.encode("utf-8"))
            <= max_chars
        ):
            current_chunk += (
                sentence + " "
                if sentence and len(sentence[-1].encode("utf-8")) == 1
                else sentence
            )
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = (
                sentence + " "
                if sentence and len(sentence[-1].encode("utf-8")) == 1
                else sentence
            )

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def infer_batch(
    abs_voice_path,
    transcript,
    gen_text_batches,
    cross_fade_duration=0.15,
):
    ema_model = load_model("F5-TTS", "F5TTS_Base", DiT, F5TTS_model_cfg, 1200000)

    audio, sr = abs_voice_path
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)

    rms = torch.sqrt(torch.mean(torch.square(audio)))
    if rms < target_rms:
        audio = audio * target_rms / rms
    if sr != target_sample_rate:
        resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
        audio = resampler(audio)
    audio = audio.to(device)

    generated_waves = []

    for i, gen_text in enumerate(tqdm.tqdm(gen_text_batches)):
        # Prepare the text
        if len(transcript[-1].encode("utf-8")) == 1:
            transcript = transcript + " "
        text_list = [transcript + gen_text]
        final_text_list = convert_char_to_pinyin(text_list)

        # Calculate duration
        abs_voice_path_len = audio.shape[-1] // hop_length
        zh_pause_punc = r"。，、；：？！"
        transcript_len = len(transcript.encode("utf-8")) + 3 * len(
            re.findall(zh_pause_punc, transcript)
        )
        gen_text_len = len(gen_text.encode("utf-8")) + 3 * len(
            re.findall(zh_pause_punc, gen_text)
        )
        duration = abs_voice_path_len + int(
            abs_voice_path_len / transcript_len * gen_text_len / speed
        )

        # inference
        with torch.inference_mode():
            generated, _ = ema_model.sample(
                cond=audio,
                text=final_text_list,
                duration=duration,
                steps=nfe_step,
                cfg_strength=cfg_strength,
                sway_sampling_coef=sway_sampling_coef,
            )

        generated = generated[:, abs_voice_path_len:, :]
        generated_mel_spec = rearrange(generated, "1 n d -> 1 d n")
        generated_wave = vocos.decode(generated_mel_spec.cpu())
        if rms < target_rms:
            generated_wave = generated_wave * rms / target_rms

        # wav -> numpy
        generated_wave = generated_wave.squeeze().cpu().numpy()

        generated_waves.append(generated_wave)

    # Combine all generated waves with cross-fading
    if cross_fade_duration <= 0:
        # Simply concatenate
        final_wave = np.concatenate(generated_waves)
    else:
        final_wave = generated_waves[0]
        for i in range(1, len(generated_waves)):
            prev_wave = final_wave
            next_wave = generated_waves[i]

            # Calculate cross-fade samples, ensuring it does not exceed wave lengths
            cross_fade_samples = int(cross_fade_duration * target_sample_rate)
            cross_fade_samples = min(cross_fade_samples, len(prev_wave), len(next_wave))

            if cross_fade_samples <= 0:
                # No overlap possible, concatenate
                final_wave = np.concatenate([prev_wave, next_wave])
                continue

            # Overlapping parts
            prev_overlap = prev_wave[-cross_fade_samples:]
            next_overlap = next_wave[:cross_fade_samples]

            # Fade out and fade in
            fade_out = np.linspace(1, 0, cross_fade_samples)
            fade_in = np.linspace(0, 1, cross_fade_samples)

            # Cross-faded overlap
            cross_faded_overlap = prev_overlap * fade_out + next_overlap * fade_in

            # Combine
            new_wave = np.concatenate(
                [
                    prev_wave[:-cross_fade_samples],
                    cross_faded_overlap,
                    next_wave[cross_fade_samples:],
                ]
            )

            final_wave = new_wave

    return final_wave


def process_voice(ref_audio_orig, transcript):
    print("Converting audio...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        aseg = AudioSegment.from_file(ref_audio_orig)

        non_silent_segs = silence.split_on_silence(
            aseg, min_silence_len=1000, silence_thresh=-50, keep_silence=1000
        )
        non_silent_wave = AudioSegment.silent(duration=0)
        for non_silent_seg in non_silent_segs:
            non_silent_wave += non_silent_seg
        aseg = non_silent_wave

        audio_duration = len(aseg)
        if audio_duration > 15000:
            print("Audio is over 15s, clipping to only first 15s.")
            aseg = aseg[:15000]
        aseg.export(f.name, format="wav")
        ref_audio = f.name

    if not transcript.strip():
        print("No reference text provided, transcribing reference audio...")
        pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-large-v3-turbo",
            torch_dtype=torch.float16,
            device=device,
        )
        transcript = pipe(
            ref_audio,
            chunk_length_s=30,
            batch_size=128,
            generate_kwargs={"task": "transcribe"},
            return_timestamps=False,
        )["text"].strip()
        print("Finished transcription")
    else:
        print("Using custom reference text...")
    return ref_audio, transcript


def infer(abs_voice_path, transcript, gen_text, cross_fade_duration=0.15):
    print(gen_text)
    # Add the functionality to ensure it ends with ". "
    if not transcript.endswith(". ") and not transcript.endswith("。"):
        if transcript.endswith("."):
            transcript += " "
        else:
            transcript += ". "

    # Split the input text into batches
    audio, sr = torchaudio.load(abs_voice_path)
    max_chars = int(
        len(transcript.encode("utf-8"))
        / (audio.shape[-1] / sr)
        * (25 - audio.shape[-1] / sr)
    )
    gen_text_batches = chunk_text(gen_text, max_chars=max_chars)
    print("transcript", transcript)
    for i, gen_text in enumerate(gen_text_batches):
        print(f"gen_text {i}", gen_text)

    print(
        f"Generating audio using F5-TTS in {len(gen_text_batches)} batches, loading models..."
    )
    return infer_batch(
        (audio, sr),
        transcript,
        gen_text_batches,
        cross_fade_duration,
    )


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes an audio file to text using the OpenAI Whisper model.

    Args:
        audio_path (str): Path to the audio file to be transcribed.
        device (str): The device to run the model on, e.g., 'cuda' or 'cpu'. Default is 'cuda'.

    Returns:
        str: The transcribed text.
    """
    transcription = ""  # Initialize reference text as empty

    if (
        not transcription.strip()
    ):  # If transcription is empty, proceed with transcription
        print("No reference text provided, transcribing reference audio...")

        # Load the automatic speech recognition pipeline
        pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-large-v3-Turbo",
            torch_dtype=torch.float16,
            device=device,
        )

        # Transcribe the audio file
        transcription = pipe(
            audio_path,
            chunk_length_s=30,
            batch_size=128,
            generate_kwargs={"task": "transcribe"},
            return_timestamps=False,
        )["text"].strip()

        # Print and return the transcribed text
        print("\nTranscribed text: ", transcription)
        print("\nFinished transcription")

        # Clean up resources
        del pipe
        torch.cuda.empty_cache()
        gc.collect()
    return transcription


def F5_text_to_speech(abs_voice_path, transcript, text_gen, output_file):
    generated_audio_segments = []
    audio = infer(abs_voice_path, transcript, text_gen)
    generated_audio_segments.append(audio)

    if generated_audio_segments:
        final_wave = np.concatenate(generated_audio_segments)
        with open(output_file, "wb") as f:
            sf.write(f.name, final_wave, target_sample_rate)
            aseg = AudioSegment.from_file(f.name)
            non_silent_segs = silence.split_on_silence(
                aseg, min_silence_len=1500, silence_thresh=-50, keep_silence=1000
            )
            non_silent_wave = AudioSegment.silent(duration=0)
            for non_silent_seg in non_silent_segs:
                non_silent_wave += non_silent_seg
            aseg = non_silent_wave
            aseg.export(f.name, format="wav")
            print(f.name)


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
    voice_path = "./abs_voice_path/"
    text = input("Please enter some text: ")
    voices = get_available_voices(voice_path)
    voice_file = pick_random_voice(voices)
    transcript = load_transcript(voice_file, voice_path)
    abs_voice_path = os.path.join(voice_path, voice_file)
    audio = F5_text_to_speech(abs_voice_path, transcript, text, "output.wav")
