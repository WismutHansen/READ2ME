import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
        """Parse transcript into list of (speaker, text) tuples"""
        # Clean transcript
        transcript = re.sub(
            r".*?(speaker1)", r"\1", transcript, flags=re.DOTALL | re.IGNORECASE
        )
        transcript = re.sub(r"\([^)]*\)", "", transcript)

        speaker_turns = []
        lines = transcript.strip().split("\n")
        for line in lines:
            if ":" in line:
                speaker, text = line.split(":", 1)
                speaker_turns.append((speaker.strip(), text.strip()))

        if not speaker_turns:
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
                voice_1 = available_voices[0]
            if not voice_2:
                voice_2 = (
                    available_voices[1]
                    if len(available_voices) > 1
                    else available_voices[0]
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
            return self._export_podcast(final_audio, transcript)

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

    def _export_podcast(self, audio: AudioSegment, transcript: str) -> str:
        """Export podcast audio and metadata"""
        try:
            # Implementation of file naming, export, and metadata addition
            output_path = os.path.join(self.current_dir, "output", "podcast.mp3")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            audio.export(output_path, format="mp3")
            self.logger.info(f"Exported podcast to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error exporting podcast: {e}")
            raise
