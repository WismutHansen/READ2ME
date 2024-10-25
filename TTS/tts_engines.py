import logging
import os
import random
import tempfile
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import numpy as np
from edge_tts import VoicesManager
from pydub import AudioSegment

from utils.F5_TTS.F5 import get_available_voices as f5_get_voices
from utils.F5_TTS.F5 import infer


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

    @abstractmethod
    async def pick_random_voice(
        self, available_voices: List[str], previous_voice: Optional[str] = None
    ) -> str:
        """Pick a random voice from a List of available voices"""
        pass


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
                await tts(text, voice_id, temp_audio.name, temp_vtt.name)
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

            wave, sr, _ = infer(
                audio_path, text, text, model="F5-TTS", remove_silence=False
            )

            if wave is None:
                raise ValueError(f"F5-TTS returned None for voice {voice_id}")

            # Convert numpy array to AudioSegment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                try:
                    # Ensure the array is normalized to [-1, 1]
                    wave = np.clip(wave, -1, 1)

                    # Convert to 16-bit PCM
                    audio_np_int16 = (wave * 32767).astype(np.int16)

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
