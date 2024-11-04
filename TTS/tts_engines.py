import logging
import os
import platform
import random
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple
from database.crud import (
    ArticleData,
    TextData,
    PodcastData,
    update_article,
    update_text,
    update_podcast,
)
import numpy as np
import torch
from edge_tts import Communicate, SubMaker, VoicesManager
from pydub import AudioSegment
from scipy.io.wavfile import write
from tqdm import tqdm
from txtsplit import txtsplit

from llm.LLM_calls import generate_title
from TTS.F5_TTS.F5 import get_available_voices as f5_get_voices
from TTS.F5_TTS.F5 import infer, load_transcript
from utils.common_utils import (
    add_mp3_tags,
    get_output_files,
    write_markdown_file,
)
from utils.env import setup_env


logger = logging.getLogger(__name__)

output_dir, task_file, img_pth, sources_file = setup_env()


class TTSEngine(ABC):
    @abstractmethod
    async def generate_audio(
        self, text: str, voice_id: str
    ) -> Tuple[AudioSegment, Optional[str]]:
        """
        Generate audio for given text using specified voice.
        Returns tuple of (AudioSegment, optional VTT file path)
        """
        pass

    @abstractmethod
    async def get_available_voices(self) -> List[str]:
        """Return list of available voice IDs"""
        pass

    async def pick_random_voice(
        self, available_voices: List[str], previous_voice: Optional[str] = None
    ) -> str:
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

    async def export_audio(
        self,
        audio: AudioSegment,
        text: str,
        title: Optional[str] = None,
        vtt_temp_file: Optional[str] = None,
        audio_type: Optional[str] = None,
        article_id: Optional[str] = None,
        text_id: Optional[int] = None,
        podcast_id: Optional[int] = None,
    ) -> str:
        """Export audio, convert to MP3 if needed, and add metadata"""
        try:
            # Generate title if not provided
            if not title:
                title = generate_title(text)
            base_file_name, output_path, md_file_name = await get_output_files(
                output_dir, title
            )

            # Convert to MP3 if the format is not already MP3
            if not output_path.endswith(".mp3"):
                mp3_file = f"{base_file_name}.mp3"
                audio.export(mp3_file, format="mp3")
                add_mp3_tags(mp3_file, title, img_pth, output_dir, audio_type)
                output_path = mp3_file
            else:
                audio.export(output_path, format="mp3")
                add_mp3_tags(output_path, title, img_pth, output_dir)
            # Write the markdown file for the text
            write_markdown_file(md_file_name, text)
            logger.info(f"Exported audio to {output_path}")

            # Handle optional VTT file if provided
            if vtt_temp_file:
                vtt_file = f"{base_file_name}.vtt"
                shutil.move(vtt_temp_file, vtt_file)

            if article_id:
                if audio_type == "url/full" or "url/tldr":
                    new_article = ArticleData(
                        md_file=md_file_name,
                        vtt_file=vtt_file if vtt_file else "",
                        audio_file=output_path,
                        img_file=img_pth,
                    )
                    update_article(article_id, new_article)
                    logging.info(
                        f"article {article_id} db entry successfully updated with audio data"
                    )

            elif text_id:
                if audio_type == "text/full" or "text/tldr":
                    new_text = TextData(
                        md_file=md_file_name,
                        vtt_file=vtt_file if vtt_file else "",
                        audio_file=output_path,
                        img_file=img_pth,
                    )
                    update_text(text_id, new_text)
                    logging.info(
                        f"article {article_id} db entry successfully updated with audio data"
                    )

            elif podcast_id:
                if audio_type == "podcast":
                    new_podcast = PodcastData(
                        audio_file=output_path,
                        img_file=img_pth,
                    )
                    update_podcast(podcast_id, new_podcast)
                    logging.info(
                        f"podcast{podcast_id} db entry successfully updated with audio data"
                    )

            return output_path
        except Exception as e:
            logger.error(f"Error exporting audio: {e}")
            raise


class EdgeTTSEngine(TTSEngine):
    async def get_available_voices(self) -> List[str]:
        voices = await VoicesManager.create()
        return [
            voice_info["Name"]
            for voice_info in voices.voices
            if "MultilingualNeural" in voice_info["Name"]
            and "en-US" in voice_info["Name"]
        ]

    async def generate_audio(
        self, text: str, voice_id: str
    ) -> Tuple[AudioSegment, Optional[str]]:
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_audio:
            with tempfile.NamedTemporaryFile(suffix=".vtt") as temp_vtt:
                # Create communicate object
                communicate = Communicate(text, voice_id)
                submaker = SubMaker()
                # Generate audio and save to temp file
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        temp_audio.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        # Handle SSML timing data if needed
                        submaker.create_sub(
                            (chunk["offset"], chunk["duration"]), chunk["text"]
                        )
                        with open(temp_vtt.name, "w", encoding="utf-8") as f:
                            f.write(submaker.generate_subs())

                temp_audio.flush()
                audio = AudioSegment.from_file(temp_audio.name)

                # Read VTT content
                with open(temp_vtt.name, "r", encoding="utf-8") as f:
                    vtt_content = f.read()

                # Create permanent VTT file if needed
                vtt_file = None
                if vtt_content.strip():
                    vtt_file = f"{temp_audio.name}.vtt"
                    with open(vtt_file, "w", encoding="utf-8") as f:
                        f.write(vtt_content)

                return audio, vtt_file


class F5TTSEngine(TTSEngine):
    def __init__(self, voice_dir: str):
        self.voice_dir = voice_dir
        self.logger = logging.getLogger(__name__)

    async def get_available_voices(self) -> List[str]:
        try:
            voices = f5_get_voices(self.voice_dir)
            self.logger.info(f"Found {len(voices)} voices in {self.voice_dir}")
            return voices
        except Exception as e:
            self.logger.error(f"Error getting available voices: {e}")
            raise

    async def generate_audio(
        self, text: str, voice_id: str
    ) -> Tuple[AudioSegment, None]:
        try:
            audio_path = os.path.join(self.voice_dir, voice_id)
            self.logger.info(f"Generating audio using voice: {audio_path}")
            ref_text = load_transcript(voice_id, self.voice_dir)
            audio, _ = infer(
                audio_path,
                ref_text,
                text,
                model="F5-TTS",
                remove_silence=True,
                speed=1.1,
            )

            sr, audio_data = audio
            if audio_data is None:
                raise ValueError(f"F5-TTS returned None for voice {voice_id}")

            # Convert numpy array to AudioSegment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                try:
                    # Ensure the array is normalized to [-1, 1]
                    audio_data = np.clip(audio_data, -1, 1)

                    # Convert to 16-bit PCM
                    audio_np_int16 = (audio_data * 32767).astype(np.int16)

                    # Create AudioSegment
                    audio_segment = AudioSegment(
                        data=audio_np_int16.tobytes(),
                        sample_width=2,  # 16-bit
                        frame_rate=sr,
                        channels=1,  # mono
                    )

                    self.logger.info(
                        f"Successfully generated audio segment of length {len(audio_segment)}ms"
                    )
                    return audio_segment, None

                except Exception as e:
                    self.logger.error(f"Error converting audio data: {e}")
                    raise
                finally:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)

        except Exception as e:
            self.logger.error(f"Error in generate_audio: {e}")
            raise


class PiperTTSEngine(TTSEngine):
    def __init__(self, voices_dir: str):
        self.voices_dir = os.path.join(voices_dir)
        self.logger = logging.getLogger(__name__)

    async def get_available_voices(self) -> List[str]:
        # List available voices based on subfolder names in the voices directory
        if not os.path.exists(self.voices_dir):
            self.logger.error(f"Voices directory '{self.voices_dir}' does not exist.")
            return []

        # Check each subdirectory for .onnx and .json files
        voice_ids = [
            folder
            for folder in os.listdir(self.voices_dir)
            if os.path.isdir(os.path.join(self.voices_dir, folder))
            and any(
                file.endswith(".onnx")
                for file in os.listdir(os.path.join(self.voices_dir, folder))
            )
            and any(
                file.endswith(".json")
                for file in os.listdir(os.path.join(self.voices_dir, folder))
            )
        ]

        self.logger.info(f"Found {len(voice_ids)} voices in {self.voices_dir}")
        return voice_ids

    async def generate_audio(
        self, text: str, voice_id: str
    ) -> Tuple[AudioSegment, None]:
        try:
            # Determine the path to the Piper binary based on the operating system
            script_folder = os.path.dirname(os.path.abspath(__file__))
            operating_system = platform.system()

            if operating_system == "Windows":
                piper_binary = os.path.join(script_folder, "piper_tts", "piper.exe")
            else:
                piper_binary = os.path.join(script_folder, "piper_tts", "piper")

            voice_folder_path = os.path.join(self.voices_dir, voice_id)

            # Verify the voice model files exist
            model_path = next(
                (
                    os.path.join(voice_folder_path, f)
                    for f in os.listdir(voice_folder_path)
                    if f.endswith(".onnx")
                ),
                None,
            )
            json_path = next(
                (
                    os.path.join(voice_folder_path, f)
                    for f in os.listdir(voice_folder_path)
                    if f.endswith(".json")
                ),
                None,
            )

            if not model_path or not json_path:
                self.logger.error(
                    "Required voice files not found in the specified voice folder."
                )
                raise FileNotFoundError("Piper model or JSON file missing")

            # Use a temporary file for the output audio
            with NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            # Construct and execute the Piper command
            command = [
                piper_binary,
                "-m",
                model_path,
                "-c",
                json_path,
                "-f",
                temp_audio_path,
                "-s",
                "0",  # Example: using voice index 0 for multi-voice models
                "--length_scale",
                "1.0",  # Set length scale (speed of speech)
            ]

            process = subprocess.run(
                command,
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Check if the process completed successfully
            if process.returncode != 0:
                self.logger.error(
                    f"Piper TTS command failed: {process.stderr.decode()}"
                )
                raise RuntimeError("Piper TTS synthesis failed")

            # Load generated audio file into AudioSegment
            audio = AudioSegment.from_file(temp_audio_path, format="wav")
            self.logger.info(f"Generated Piper TTS audio for voice_id {voice_id}")
            return audio, None
        except Exception as e:
            self.logger.error(f"Error generating audio with Piper TTS: {e}")
            raise


class StyleTTS2Engine(TTSEngine):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def get_available_voices(self) -> List[str]:
        # Only one voice for StyleTTS2
        return ["styletts2_default_voice"]

    async def generate_audio(
        self, text: str, voice_id: str
    ) -> Tuple[AudioSegment, None]:
        from .styletts2.ljspeechimportable import inference

        try:
            # Ensure the text is valid and within length limits
            if not text.strip():
                self.logger.error("Text input is empty.")
                raise ValueError("Empty text input")

            if len(text) > 150000:
                self.logger.error("Text must be <150k characters")
                raise ValueError("Text is too long")

            # Split the text and synthesize each segment
            texts = txtsplit(text)
            audios = []
            noise = torch.randn(1, 1, 256).to(
                "cuda" if torch.cuda.is_available() else "cpu"
            )

            for t in tqdm(texts, desc="Synthesizing with StyleTTS2"):
                audio_segment = inference(
                    t, noise, diffusion_steps=5, embedding_scale=1
                )
                if audio_segment is not None:
                    audios.append(audio_segment)
                else:
                    self.logger.error(f"Inference returned None for text segment: {t}")

            if not audios:
                raise ValueError("No audio segments were generated")

            # Concatenate all audio segments and save to a temporary WAV file
            full_audio = np.concatenate(audios)
            with NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
                write(temp_wav_file.name, 24000, full_audio)
                temp_wav_path = temp_wav_file.name

            # Load the temporary WAV file as an AudioSegment
            audio = AudioSegment.from_file(temp_wav_path, format="wav")
            return audio, None
        except Exception as e:
            self.logger.error(f"Error generating audio with StyleTTS2: {e}")
            raise
