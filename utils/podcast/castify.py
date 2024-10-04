import os
import random
from pydub import AudioSegment
import asyncio
from edge_tts import VoicesManager
from ..synthesize import tts
from ..common_utils import get_output_files, add_mp3_tags
from ..env import setup_env
from llm.LLM_calls import generate_title

# Get the current directory of the script
current_dir = os.path.dirname(os.path.abspath(__file__))

output_dir, task_file, img_pth, sources_file = setup_env()


def parse_transcript(transcript):
    """
    Parses the transcript into a list of (speaker, text) tuples.
    """
    speaker_turns = []
    lines = transcript.strip().split("\n")
    for line in lines:
        if ":" in line:
            speaker, text = line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()
            speaker_turns.append((speaker, text))
    return speaker_turns


async def create_podcast_audio(
    transcript: str, voice_1: str = None, voice_2: str = None
):
    """
    Creates the podcast audio from the transcript using the edge_tts library.
    """
    # Parse the transcript
    speaker_turns = parse_transcript(transcript)

    # Identify speakers and assign voices and numbering
    speakers = {}
    speaker_voices = {}

    # Get available voices if not provided
    if not voice_1 or not voice_2:
        voices = await VoicesManager.create()
        multilingual_voices = [
            voice_info
            for voice_info in voices.voices
            if "MultilingualNeural" in voice_info["Name"]
            and "en-US" in voice_info["Name"]
        ]
        if not multilingual_voices:
            raise ValueError("No MultilingualNeural voices found")

    # Assign voices to speakers
    for speaker, _ in speaker_turns:
        if speaker not in speakers:
            speakers[speaker] = len(speakers) + 1  # Assign speaker number

            # Assign voices if not provided
            if len(speakers) == 1:
                speaker_voices[speaker] = (
                    voice_1 if voice_1 else random.choice(multilingual_voices)["Name"]
                )
                speaker_1_name = speaker  # Save for later
            elif len(speakers) == 2:
                speaker_voices[speaker] = (
                    voice_2 if voice_2 else random.choice(multilingual_voices)["Name"]
                )
                speaker_2_name = speaker  # Save for later

    # Initialize variables to keep track of timing
    current_time = 0  # in milliseconds
    speaker_timing = {speaker: [] for speaker in speakers}

    # Process each speaker turn and record timing
    for speaker, text in speaker_turns:
        voice = speaker_voices[speaker]
        segment_index = len(speaker_timing[speaker]) + 1
        filename = os.path.join(current_dir, f"{speaker}_segment_{segment_index}.mp3")

        # Generate the audio file using the TTS function
        await tts(text, voice, filename)

        # Load the audio segment
        try:
            audio = AudioSegment.from_file(filename)
        except Exception as e:
            print(f"Error loading audio file {filename}: {e}")
            continue

        # Record the timing for this segment
        speaker_timing[speaker].append((current_time, audio))

        # Update current time
        current_time += len(audio)

    # Determine the total duration of the podcast
    total_duration = max(
        [
            start_time + len(audio)
            for timings in speaker_timing.values()
            for (start_time, audio) in timings
        ]
    )

    # Create empty AudioSegment for each speaker
    speaker_tracks = {}
    for speaker in speakers:
        speaker_tracks[speaker] = AudioSegment.silent(duration=total_duration)

    # Place each audio segment in the correct position on its speaker's track
    for speaker, timings in speaker_timing.items():
        for start_time, audio in timings:
            # Overlay the audio segment at the correct time
            speaker_tracks[speaker] = speaker_tracks[speaker].overlay(
                audio, position=start_time
            )

    # Pan each track
    speaker_tracks[speaker_1_name] = speaker_tracks[speaker_1_name].pan(
        -0.2
    )  # Slightly left
    speaker_tracks[speaker_2_name] = speaker_tracks[speaker_2_name].pan(
        0.2
    )  # Slightly right

    # Mix the two tracks
    combined_audio = speaker_tracks[speaker_1_name].overlay(
        speaker_tracks[speaker_2_name]
    )

    # Export the final audio to the podcast directory
    podcast_number = 1
    while os.path.exists(os.path.join(current_dir, f"podcast_{podcast_number}.mp3")):
        podcast_number += 1
    title = f"podcast_{podcast_number}"
    base_file_name, mp3_file, md_file = await get_output_files(output_dir, title)
    # output_file = os.path.join(current_dir, f"podcast_{podcast_number}.mp3")

    combined_audio.export(mp3_file, format="mp3")

    add_mp3_tags(mp3_file, title, img_pth, output_dir)

    # Delete individual audio segments
    for speaker, timings in speaker_timing.items():
        for start_time, audio in timings:
            segment_index = timings.index((start_time, audio)) + 1
            filename = os.path.join(
                current_dir, f"{speaker}_segment_{segment_index}.mp3"
            )
            if os.path.exists(filename):
                os.remove(filename)
    print(f"Podcast audio has been generated as '{mp3_file}'.")


# Example usage
if __name__ == "__main__":
    import asyncio

    transcript = """
    Alex: Hey, did you hear about the new Python release?
    Taylor: Oh, no, I haven't. What's new in it?
    Alex: Well, they added some really cool features like pattern matching.
    Taylor: That's awesome! I was waiting for that feature.
    """

    # Running the asyncio function
    asyncio.run(create_podcast_audio(transcript))
