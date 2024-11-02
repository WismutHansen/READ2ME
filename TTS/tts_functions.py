import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from database.state import get_current_podcast
from pydub import AudioSegment
from .tts_engines import TTSEngine


@dataclass
class SpeakerTiming:
    start_time: int
    audio: AudioSegment
    vtt_file: Optional[str] = None


@dataclass
class SpeakerConfig:
    name: str
    voice_id: str
    pan: float = 0.0


class PodcastGenerator:
    def __init__(self, tts_engine: TTSEngine):
        self.tts_engine = tts_engine
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def parse_transcript(self, transcript: str) -> List[Tuple[str, str]]:
        """
        Parse transcript into list of (speaker, text) tuples.
        Handles various speaker label formats and removes parenthetical notes.

        Handles formats like:
        - Speaker1: Text (laughs) more text
        - Speaker 1: Text (pauses) more text
        - speaker1: Text (clears throat) more text

        Args:
            transcript (str): Raw transcript text

        Returns:
            List[Tuple[str, str]]: List of (speaker, text) tuples

        Raises:
            ValueError: If no valid speaker turns are found
        """
        # Clean and normalize the transcript
        transcript = transcript.strip()

        # More flexible regex pattern that handles variations
        pattern = r"\s*(?:speaker\s*[12]|SPEAKER\s*[12]|Speaker\s*[12]):\s*"

        # Split the transcript by speaker tags
        speaker_blocks = re.split(pattern, transcript, flags=re.IGNORECASE)

        # Remove any empty strings and strip whitespace
        speaker_blocks = [block.strip() for block in speaker_blocks if block.strip()]

        # Function to clean text blocks
        def clean_text(text: str) -> str:
            # Remove parenthetical notes
            text = re.sub(r"\s*\([^)]+\)\s*", " ", text)
            # Clean up any resulting double spaces
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        # Group the blocks into (speaker, text) pairs
        speaker_turns = []
        speaker_number = 1  # Keep track of alternating speakers

        # Handle the case where the first block might be speaker text without a speaker label
        if speaker_blocks and not re.match(pattern, transcript, flags=re.IGNORECASE):
            cleaned_text = clean_text(speaker_blocks[0])
            if cleaned_text:  # Only add if there's text after cleaning
                speaker_turns.append((f"speaker{speaker_number}", cleaned_text))
            speaker_number = 2
            speaker_blocks = speaker_blocks[1:]

        # Process the remaining blocks
        for text in speaker_blocks:
            cleaned_text = clean_text(text)
            if cleaned_text:  # Only add if there's text after cleaning
                speaker_turns.append((f"speaker{speaker_number}", cleaned_text))
                # Toggle between speaker1 and speaker2
                speaker_number = 1 if speaker_number == 2 else 2

        if not speaker_turns:
            self.logger.error("No valid speaker turns found in transcript")
            raise ValueError("No valid speaker turns found in transcript")

        self.logger.info(f"Parsed {len(speaker_turns)} speaker turns")
        return speaker_turns

    async def assign_voices(
        self,
        speaker_turns: List[Tuple[str, str]],
        voice_1: Optional[str] = None,
        voice_2: Optional[str] = None,
    ) -> Dict[str, SpeakerConfig]:
        """Assign voices to speakers"""
        speakers = {}

        try:
            available_voices = await self.tts_engine.get_available_voices()
            self.logger.info(f"Available voices: {available_voices}")

            if not available_voices:
                raise ValueError("No voices available from TTS engine")

            if not voice_1:
                voice_1 = await self.tts_engine.pick_random_voice(available_voices)
                # voice_1 = available_voices[0]
            if not voice_2:
                voice_2 = await self.tts_engine.pick_random_voice(
                    available_voices, voice_1
                )

        except Exception as e:
            self.logger.error(f"Error getting available voices: {e}")
            raise

        for speaker, _ in speaker_turns:
            if speaker not in speakers:
                if len(speakers) == 0:
                    speakers[speaker] = SpeakerConfig(speaker, voice_1, -0.2)
                    self.logger.info(f"Assigned voice {voice_1} to {speaker}")
                elif len(speakers) == 1:
                    speakers[speaker] = SpeakerConfig(speaker, voice_2, 0.2)
                    self.logger.info(f"Assigned voice {voice_2} to {speaker}")

        return speakers

    async def create_podcast_audio(
        self,
        transcript: str,
        voice_1: Optional[str] = None,
        voice_2: Optional[str] = None,
    ) -> str:
        """Create podcast audio file from transcript"""
        try:
            speaker_turns = self.parse_transcript(transcript)
            speakers = await self.assign_voices(speaker_turns, voice_1, voice_2)
            self.logger.info(speakers)
            # Track timing and audio segments
            current_time = 0
            speaker_timing: Dict[str, List[SpeakerTiming]] = {s: [] for s in speakers}

            # Generate audio for each turn
            for speaker, text in speaker_turns:
                config = speakers[speaker]
                try:
                    self.logger.info(f"Generating audio for {speaker}: {text[:50]}...")
                    audio, vtt_file = await self.tts_engine.generate_audio(
                        text, config.voice_id
                    )
                    speaker_timing[speaker].append(
                        SpeakerTiming(current_time, audio, vtt_file)
                    )
                    current_time += len(audio)
                except Exception as e:
                    self.logger.error(f"Error generating audio for {speaker}: {e}")
                    continue

            # Verify we have generated audio segments
            if not any(
                timing for timings in speaker_timing.values() for timing in timings
            ):
                raise ValueError("No audio segments were successfully generated")

            # Mix audio tracks
            total_duration = max(
                (timing.start_time + len(timing.audio))
                for timings in speaker_timing.values()
                for timing in timings
            )

            # Create and mix tracks
            final_audio = self._mix_tracks(speakers, speaker_timing, total_duration)

            # Export and return path
            return await self.tts_engine.export_audio(final_audio, transcript)

        except Exception as e:
            self.logger.error(f"Error creating podcast: {e}")
            raise

    def _mix_tracks(
        self,
        speakers: Dict[str, SpeakerConfig],
        speaker_timing: Dict[str, List[SpeakerTiming]],
        total_duration: int,
    ) -> AudioSegment:
        """Mix individual speaker tracks into final audio"""
        speaker_tracks = {}

        for speaker in speakers:
            track = AudioSegment.silent(duration=total_duration)

            # Add all segments for this speaker
            for timing in speaker_timing[speaker]:
                track = track.overlay(timing.audio, position=timing.start_time)

            # Apply panning
            track = track.pan(speakers[speaker].pan)
            speaker_tracks[speaker] = track

        # Mix all tracks
        final_audio = speaker_tracks[list(speakers.keys())[0]]
        for track in list(speaker_tracks.values())[1:]:
            final_audio = final_audio.overlay(track)

        return final_audio

    def _add_podcast_data_db(
        self,
    ):
        # if podcast_article:
        pass
