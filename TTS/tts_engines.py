#!/usr/bin/env python3
# tts_engines.py
# -*- coding: utf-8 -*-
import logging
import mimetypes
import os
import random
import shutil
import sys
import tempfile
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import httpx
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from dotenv import load_dotenv
from edge_tts import Communicate, SubMaker, VoicesManager
from pydub import AudioSegment
from pydub.effects import speedup
from tqdm import tqdm

from database.crud import (
    ArticleData,
    PodcastData,
    TextData,
    update_article,
    update_podcast,
    update_text,
)
from llm.LLM_calls import generate_title
from llm.Local_Ollama import unload_ollama_model
from utils.common_utils import (
    add_mp3_tags,
    get_output_files,
    write_markdown_file,
)
from utils.env import setup_env
from utils.text_processor import AdvancedTextPreprocessor

load_dotenv()

logger = logging.getLogger(__name__)

output_dir, task_file, img_pth, sources_file = setup_env()

_TEXT_PREPROCESSOR = AdvancedTextPreprocessor(
    min_chars=20,
    language="english",
    keep_acronyms=True,
)

LOW_VRAM = os.environ.get("LOW_VRAM", "False").lower() == "true"
LLM_ENGINE = os.environ.get("LLM_ENGINE", "Ollama")


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
            if speed is None:
                speed = 1.1
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
                return audio, vtt_file
            else:
                os.unlink(temp_vtt.name)  # Remove empty subtitle file
                _ = None
                return audio, _

        finally:
            # Cleanup temp files
            try:
                os.unlink(temp_audio.name)
            except Exception as e:
                print(f"Warning: Failed to delete temp audio file: {e}")

            try:
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


class ChatterboxEngine(TTSEngine):
    def __init__(self, voice_dir: str, device=None):
        """
        Initialize Chatterbox TTS Engine.
        """
        self.device = self._detect_device(device)
        print(f"Using {self.device} device for Chatterbox TTS.", file=sys.stderr)
        self.model = None  # Initialize model to None
        self.sample_rate = (
            None  # Initialize sample_rate to None, will be set after model loading
        )
        self.logger = logging.getLogger(__name__)
        self.voice_dir = voice_dir
        # Set CUDA debugging environment variables for better error reporting
        if self.device == "cuda":
            os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
            os.environ["TORCH_USE_CUDA_DSA"] = "1"
            # Set memory allocation strategy to reduce fragmentation
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
        # print("Chatterbox model loaded", file=sys.stderr) # Model is no longer loaded at init

    def _detect_device(self, device):
        if device is not None:
            return device
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def load_model(self):
        """Loads the ChatterboxTTS model."""
        if self.model is not None:
            self.logger.info("Model is already loaded.")
            return

        # Save original torch.load and restore after model loading
        original_torch_load = torch.load
        try:
            # Set CUDA error handling to prevent silent failures
            if self.device == "cuda":
                torch.backends.cudnn.enabled = True
                torch.backends.cudnn.benchmark = False  # Disable for stability
                torch.backends.cudnn.deterministic = True
                
            if self.device == "mps":
                # Apply MPS device mapping patch
                def patched_torch_load(*args, **kwargs):
                    if "map_location" not in kwargs:
                        kwargs["map_location"] = torch.device(self.device)
                    return original_torch_load(*args, **kwargs)

                torch.load = patched_torch_load

            self.logger.info(f"Loading ChatterboxTTS model on {self.device}...")

            # Suppress specific deprecation warnings during model loading
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=FutureWarning, module="diffusers"
                )
                warnings.filterwarnings(
                    "ignore", message=".*LoRACompatibleLinear.*", category=FutureWarning
                )
                warnings.filterwarnings(
                    "ignore",
                    message=".*torch.backends.cuda.sdp_kernel.*",
                    category=FutureWarning,
                )
                warnings.filterwarnings(
                    "ignore", message=".*past_key_values.*", category=FutureWarning
                )
                self.model = ChatterboxTTS.from_pretrained(device=self.device)

            self.sample_rate = self.model.sr  # Set sample_rate after model is loaded
            self.logger.info("ChatterboxTTS model loaded successfully.")
            print("Chatterbox model loaded", file=sys.stderr)
        finally:
            # Always restore torch.load
            torch.load = original_torch_load

    def unload_model(self):
        """Unloads the ChatterboxTTS model and frees VRAM."""
        if self.model is None:
            self.logger.info("Model is not loaded.")
            return

        self.logger.info("Unloading ChatterboxTTS model...")
        del self.model
        self.model = None
        self.sample_rate = None  # Reset sample_rate
        
        # Force garbage collection to free memory
        import gc
        gc.collect()
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
            # Force synchronization to ensure CUDA operations complete
            torch.cuda.synchronize()
            self.logger.info("CUDA cache emptied and synchronized.")
        elif self.device == "mps":
            # For MPS, there isn't a direct equivalent to empty_cache that is as impactful
            # as for CUDA. Re-assigning to None and relying on Python's GC is the primary way.
            # torch.mps.empty_cache() # This function exists but its utility is debated for MPS
            pass
        self.logger.info("ChatterboxTTS model unloaded.")
        print("Chatterbox model unloaded", file=sys.stderr)

    async def get_available_voices(self) -> list:
        """
        Scans the given directory for available voices by matching audio and .txt files.

        Args:
            directory (str): Path to the directory containing audio and .txt files.

        Returns:
            list: A list of available voice filenames (including their extensions).
        """
        available_voices = []

        # Get list of all audio and .txt files in the directory

        files = os.listdir(self.voice_dir)

        audio_files = set()
        for f in files:
            mime_type, _ = mimetypes.guess_type(f)  # single call
            if mime_type and mime_type.startswith("audio"):
                audio_files.add(f)

        # Find common base filenames (without extensions) that have both audio and .txt files
        for audio_file in audio_files:
            os.path.splitext(audio_file)[0]  # Extract the filename without extension
            available_voices.append(audio_file)  # Append the full audio filename

        return available_voices

    async def generate_audio(
        self,
        text: str,
        voice_id: str,
        speed: Optional[float] = 1.0,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[AudioSegment, None]:
        """
        Generate TTS in ≥20-character chunks using AdvancedTextPreprocessor,
        then concatenate the resulting AudioSegments.
        """
        if LOW_VRAM and LLM_ENGINE == "Ollama":
            from llm.Local_Ollama import unload_ollama_model, force_cuda_cleanup
            unload_ollama_model()
            force_cuda_cleanup()  # Aggressive memory cleanup
            # Give Ollama time to fully unload before proceeding
            import time
            time.sleep(5)  # Further increased wait time for complete cleanup

        # Check available CUDA memory before loading model
        if self.device == "cuda":
            try:
                memory_free = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
                memory_free_gb = memory_free / (1024**3)
                self.logger.info(f"Available CUDA memory before loading: {memory_free_gb:.2f} GB")
                
                # If less than 2GB free, force additional cleanup
                if memory_free_gb < 2.0:
                    self.logger.warning("Low CUDA memory detected, forcing additional cleanup")
                    from llm.Local_Ollama import force_cuda_cleanup
                    force_cuda_cleanup()
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not check CUDA memory: {e}")
        
        self.load_model()  # Ensure model is loaded

        # Temporarily increase logging level to suppress verbose output
        original_log_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)

        try:
            # 1. chunk input text with your pre-processor
            chunks: List[str] = _TEXT_PREPROCESSOR.preprocess_text(text)

            segments: List[AudioSegment] = []

            # 2. TTS call per chunk with progress bar
            progress_bar = tqdm(chunks, desc="Generating TTS", unit="chunk")
            for idx, chunk in enumerate(progress_bar, 1):
                # Report progress if callback is provided
                if progress_callback:
                    progress = int((idx - 1) / len(chunks) * 100)
                    await progress_callback(progress)

                # Suppress warnings and disable internal progress bars during inference
                import warnings
                import io
                from contextlib import redirect_stderr, redirect_stdout

                try:
                    with (
                        warnings.catch_warnings(),
                        redirect_stderr(io.StringIO()),
                        redirect_stdout(io.StringIO()),
                    ):
                        warnings.filterwarnings("ignore")

                        # Temporarily disable tqdm for internal model operations
                        original_tqdm = None
                        try:
                            import tqdm as tqdm_module

                            original_tqdm = tqdm_module.tqdm
                            # Replace tqdm with a no-op version
                            tqdm_module.tqdm = (
                                lambda *args, **kwargs: iter(args[0]) if args else iter([])
                            )
                            
                            # Validate chunk before processing to avoid index errors  
                            if not chunk or len(chunk.strip()) == 0:
                                self.logger.warning(f"Skipping empty chunk {idx}")
                                continue
                                
                            # Limit chunk length to prevent tensor size issues
                            if len(chunk) > 500:  # Reasonable limit for TTS chunks
                                chunk = chunk[:500] + "..."
                                self.logger.warning(f"Truncated chunk {idx} to 500 characters")

                            if voice_id:
                                prompt_path = await self.get_voice_file(voice_id)
                                wav = self.model.generate(
                                    text=chunk, audio_prompt_path=prompt_path
                                )
                            else:
                                wav = self.model.generate(chunk)
                        finally:
                            # Restore original tqdm
                            if original_tqdm:
                                tqdm_module.tqdm = original_tqdm
                                
                except (RuntimeError, torch.cuda.OutOfMemoryError) as e:
                    if "device-side assert" in str(e) or "CUDA error" in str(e):
                        self.logger.error(f"CUDA assertion error in chunk {idx}: {e}")
                        
                        # Try to fallback to CPU if CUDA keeps failing
                        if self.device == "cuda":
                            self.logger.warning("Falling back to CPU due to persistent CUDA errors")
                            self.unload_model()
                            self.device = "cpu"
                            self.load_model()
                            
                            # Retry the chunk with CPU
                            try:
                                if voice_id:
                                    prompt_path = await self.get_voice_file(voice_id)
                                    wav = self.model.generate(
                                        text=chunk, audio_prompt_path=prompt_path
                                    )
                                else:
                                    wav = self.model.generate(chunk)
                            except Exception as cpu_error:
                                self.logger.error(f"CPU fallback also failed for chunk {idx}: {cpu_error}")
                                continue  # Skip this chunk
                        else:
                            # Already on CPU or different device, skip this chunk
                            self.logger.error(f"Skipping chunk {idx} due to error: '{chunk[:50]}...'")
                            continue
                    else:
                        raise  # Re-raise if it's a different error

                # 3. temp-file hop self.model → pydub
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    # Ensure model and sample_rate are available
                    if self.model is None or self.sample_rate is None:
                        raise RuntimeError(
                            "Model or sample rate not initialized. Load the model first."
                        )
                    _ = ta.save(tmp_path, wav, self.sample_rate)

                seg = AudioSegment.from_wav(tmp_path)
                os.unlink(tmp_path)

                segments.append(seg)

                # Update progress bar description with current chunk info
                progress_bar.set_postfix(
                    {"chars": len(chunk), "duration": f"{len(seg)}ms"}
                )

            progress_bar.close()

            # 4. concatenate all segments
            audio_segment: AudioSegment = sum(segments[1:], segments[0])

            # 5. optional speed adjustment
            if speed and abs(speed - 1.0) > 1e-3:
                audio_segment = speedup(audio_segment, playback_speed=speed)

            # Report completion
            if progress_callback:
                await progress_callback(100)

            self.logger.info(f"TTS composite duration: {len(audio_segment)} ms")
            return audio_segment, None

        except Exception as e:
            self.logger.error(f"TTS generation error: {e}")
            raise
        finally:
            # Restore original logging level
            logging.getLogger().setLevel(original_log_level)
            self.unload_model()  # Ensure model is unloaded
            
            # Additional cleanup for LOW_VRAM systems
            if LOW_VRAM:
                from llm.Local_Ollama import force_cuda_cleanup
                force_cuda_cleanup()

    async def get_voice_file(self, voice_id: str) -> str:
        # Define supported audio MIME types
        supported_mime_prefixes = ["audio"]

        voice_path = os.path.join(self.voice_dir, f"{voice_id}")
        if os.path.exists(voice_path):
            mime_type, _ = mimetypes.guess_type(voice_path)
            if mime_type and any(
                mime_type.startswith(prefix) for prefix in supported_mime_prefixes
            ):
                return voice_path

        raise FileNotFoundError(f"No supported audio file found for {voice_id}")
