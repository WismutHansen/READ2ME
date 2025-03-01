#!/usr/bin/env python3
# tts_engines.py
# -*- coding: utf-8 -*-
import logging
import os

import random
import shutil

import tempfile
from abc import ABC, abstractmethod

from typing import List, Optional, Tuple

import httpx
from dotenv import load_dotenv

from edge_tts import Communicate, SubMaker, VoicesManager
from pydub import AudioSegment

from database.crud import (
    ArticleData,
    PodcastData,
    TextData,
    update_article,
    update_podcast,
    update_text,
)
from llm.LLM_calls import generate_title

from utils.common_utils import (
    add_mp3_tags,
    get_output_files,
    write_markdown_file,
)
from utils.env import setup_env

load_dotenv()

logger = logging.getLogger(__name__)

output_dir, task_file, img_pth, sources_file = setup_env()


class TTSEngine(ABC):
    @abstractmethod
    async def generate_audio(
        self, text: str, voice_id: str, speed: Optional[float]
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
        text_id: Optional[str] = None,
        podcast_id: Optional[str] = None,
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
                        markdown_file=md_file_name,
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
                        markdown_file=md_file_name,
                        audio_file=output_path,
                        img_file=img_pth,
                    )
                    update_text(text_id, new_text)
                    logging.info(
                        f"Text with {text_id} db entry successfully updated with audio data"
                    )

            elif podcast_id:
                if audio_type == "podcast":
                    new_podcast = PodcastData(
                        audio_file=output_path,
                        img_file=img_pth,
                    )
                    update_podcast(podcast_id, new_podcast)
                    logging.info(
                        f"Podcast {podcast_id} db entry successfully updated with audio data"
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
        self, text: str, voice_id: str, speed: Optional[float] = 1.1
    ) -> Tuple[AudioSegment, Optional[str]]:
        # Create temp files but don't use context manager
        temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_vtt = tempfile.NamedTemporaryFile(suffix=".vtt", delete=False)

        try:
            # Convert speed to EdgeTTS format (e.g., "+10%")
            rate = f"{int((speed - 1) * 100):+d}%"

            # Initialize EdgeTTS Communicate
            communicate = Communicate(text, voice_id, rate=rate)

            # Subtitle handler
            submaker = SubMaker()

            # Generate audio
            async for message in communicate.stream():
                if message["type"] == "audio" and "data" in message:
                    temp_audio.write(message["data"])
                elif message["type"] == "WordBoundary":
                    submaker.feed(message)

            # Write subtitles if available
            with open(temp_vtt.name, "w", encoding="utf-8") as f:
                f.write(submaker.get_srt())

            temp_audio.flush()
            temp_audio.close()
            audio = AudioSegment.from_file(temp_audio.name)

            if os.path.getsize(temp_vtt.name) > 0:
                vtt_file = temp_vtt.name  # Keep the file
            else:
                os.unlink(temp_vtt.name)  # Remove empty subtitle file

            return audio, vtt_file

        finally:
            # Cleanup temp files
            try:
                os.unlink(temp_audio.name)
            except Exception as e:
                print(f"Warning: Failed to delete temp audio file: {e}")

            try:
                if vtt_file is None:
                    os.unlink(temp_vtt.name)
            except Exception as e:
                print(f"Warning: Failed to delete temp VTT file: {e}")


class OpenAITTSEngine(TTSEngine):
    """
    OpenAI Text-To-Speech (TTS) engine that uses OpenAI's API to generate speech.
    """

    def __init__(self) -> None:
        """
        Initialize the OpenAI TTS Engine with the API key and base URL from environment variables.

        Raises:
            ValueError: If no OpenAI API key is found in the environment variables.
        """
        self.logger = logging.getLogger(__name__)

        # Retrieve base URL; log a warning if not explicitly set.
        base_url = os.getenv("OPENAI_TTS_BASE_URL")
        if not base_url:
            self.logger.warning(
                "No OPENAI_TTS_BASE_URL found; using default: https://api.openai.com/v1/audio/speech"
            )
            base_url = "https://api.openai.com/v1/audio/speech"

        # Retrieve API key; raise an exception if missing.
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = (
                "No OpenAI API key found in environment variables. "
                "Please include it in the .env file as OPENAI_API_KEY."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.api_key = api_key
        self.base_url = base_url
        self.voices = [
            "alloy",
            "echo",
            "fable",
            "onyx",
            "nova",
            "shimmer",
        ]

        self.logger.info(
            "OpenAITTSEngine initialized successfully with provided API key."
        )

    async def get_available_voices(self) -> List[str]:
        """Return list of available voice IDs."""
        return self.voices

    async def generate_audio(
        self, text: str, voice_id: str, speed: Optional[float] = 1.0
    ) -> Tuple[AudioSegment, None]:
        """
        Generate audio using OpenAI's TTS API.

        Args:
            text (str): Text to synthesize.
            voice_id (str): Voice ID (from OpenAI's supported voices).
            speed (Optional[float]): Speech speed (not directly supported by OpenAI).

        Returns:
            Tuple[AudioSegment, None]: Generated audio and optional VTT file path.
        """
        try:
            # Validate voice_id
            if voice_id not in self.voices:
                raise ValueError(
                    f"Invalid voice_id '{voice_id}'. Available voices: {self.voices}"
                )

            # Prepare API request payload
            payload = {
                "model": "tts-1",  # OpenAI's TTS model
                "voice": voice_id,
                "input": text,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Make async API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

            # Check response status
            if response.status_code != 200:
                self.logger.error(f"OpenAI TTS API Error: {response.text}")
                raise RuntimeError(f"Failed to generate TTS: {response.text}")

            # Save audio to a temporary file
            temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_audio.write(response.content)
            temp_audio.flush()
            temp_audio.close()

            # Load the audio file into an AudioSegment
            audio = AudioSegment.from_file(temp_audio.name, format="mp3")
            self.logger.info(
                f"Successfully generated audio with OpenAI TTS ({voice_id})"
            )

            return audio, None

        except Exception as e:
            self.logger.error(f"Error in OpenAI TTS generation: {e}")
            raise


class KokoroTTSEngine(TTSEngine):
    def __init__(self):
        """
        Initialize Kokoro TTS Engine.
        """
        base_url = os.getenv("KOKORO_TTS_URL", "http://localhost:8880/v1")
        self.api_base_url = base_url.rstrip("/")  # Ensure no trailing slash
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Content-Type": "application/json",
        }

    async def get_available_voices(self) -> List[str]:
        """
        Fetch and return a filtered list of available voices from the Kokoro TTS API.

        This function:
        - Retrieves the list of voices from the API.
        - Filters out voices that do not start with "af" or "am" for now
        - Excludes the voice "af_nicole" since it's a whispering voice and it doesnt make much sense for news articles

        Returns:
            List[str]: A list of voice names that match the criteria.

        Raises:
            RuntimeError: If the API request fails.
            Exception: For any unexpected errors.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/audio/voices", headers=self.headers
                )

            if response.status_code != 200:
                self.logger.error(f"Kokoro API Error: {response.text}")
                raise RuntimeError(f"Failed to fetch voices: {response.text}")

            # Extract the list of voices safely
            voices_data: dict = response.json()
            voices: List[str] = voices_data.get("voices", [])

            # Apply filtering criteria
            filtered_voices: List[str] = [
                voice
                for voice in voices
                if (voice.startswith(("af", "am")) and voice != "af_nicole")
            ]

            if not filtered_voices:
                self.logger.warning("No matching voices found in Kokoro API response.")

            self.logger.info(f"Filtered Kokoro TTS voices: {filtered_voices}")
            return filtered_voices

        except Exception as e:
            self.logger.error(f"Error fetching Kokoro TTS voices: {e}")
            raise

    async def generate_audio(
        self, text: str, voice_id: str, speed: Optional[float] = 1.3
    ) -> Tuple[AudioSegment, None]:
        """
        Generate audio using the local Kokoro TTS via the OpenAI client.
        """
        try:
            self.logger.debug(f"Full text being sent to TTS: {text}")
            self.logger.info(
                f"Requesting TTS from {self.api_base_url} with voice={voice_id}, text length: {len(text)}"
            )

            # Match the API requirements
            payload = {
                "input": text,
                "voice": voice_id,
                "model": "tts-1",
                "response_format": "mp3",
                "speed": speed,
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_base_url}/audio/speech",
                        json=payload,
                        headers=self.headers,
                        timeout=300.0,
                    )

                    if response.status_code != 200:
                        raise Exception(f"API call failed: {response.text}")

                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp3", delete=False
                    ) as tmp_file:
                        tmp_file_path = tmp_file.name
                        content = response.content
                        self.logger.debug(
                            f"Response content size: {len(content)} bytes"
                        )
                        tmp_file.write(content)

                    # Load the audio file into an AudioSegment
                    audio_segment = AudioSegment.from_mp3(tmp_file_path)
                    self.logger.info(
                        f"Generated audio duration: {len(audio_segment)}ms for text of length {len(text)}"
                    )

                    # Clean up
                    os.unlink(tmp_file_path)

                    return audio_segment, None

            except Exception as e:
                self.logger.error(f"Error in TTS request: {str(e)}")
                raise

        except Exception as e:
            self.logger.error(f"Error in Kokoro TTS generation: {e}")
            raise
