import os
import re
import random
from pydub import AudioSegment
import asyncio
from edge_tts import VoicesManager
from ..synthesize import tts
from ..common_utils import get_output_files, add_mp3_tags, write_markdown_file
from ..env import setup_env
from llm.LLM_calls import generate_title
import logging

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
            speaker = speaker.strip()  # Ensure any extra whitespace is removed
            text = text.strip()
            speaker_turns.append((speaker, text))
    return speaker_turns


async def create_podcast_audio(
    transcript: str, voice_1: str = None, voice_2: str = None
):
    """
    Creates the podcast audio from the transcript using the edge_tts library.
    """
    # Remove everything up until the first occurrence of the word "speaker1"
    transcript = re.sub(
        r".*?(speaker1)", r"\1", transcript, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove any speaker notes in (*) that the LLM might put into the script
    transcript = re.sub(r"\([^)]*\)", "", transcript)

    # Parse the transcript into a list of speaker, text
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
        logging.info("Checking available voices")
        if not multilingual_voices:
            logging.error("No MultilingualNeural voices found")
            raise ValueError("No MultilingualNeural voices found")

    # Assign voices to speakers
    for speaker, _ in speaker_turns:
        if speaker not in speakers:
            speakers[speaker] = len(speakers) + 1  # Assign speaker number

            # Assign voices if not provided
            if len(speakers) == 1:
                # Assign a voice for speaker 1
                speaker_voices[speaker] = (
                    voice_1 if voice_1 else random.choice(multilingual_voices)["Name"]
                )
                speaker_1_name = speaker  # Save for later
                voice_1 = speaker_voices[
                    speaker
                ]  # Store the assigned voice for exclusion later
                logging.info(f"Voice for Speaker 1: {voice_1}")
            elif len(speakers) == 2:
                # Remove the chosen voice_1 from the list to ensure a different voice is picked
                available_voices = [
                    voice_info
                    for voice_info in multilingual_voices
                    if voice_info["Name"] != voice_1
                ]
                if not available_voices:
                    logging.error("No remaining voices available for speaker 2")
                    raise ValueError("No remaining voices available for speaker 2")

                speaker_voices[speaker] = (
                    voice_2 if voice_2 else random.choice(available_voices)["Name"]
                )
                speaker_2_name = speaker  # Save for later
                logging.info(f"Voice for Speaker 2: {speaker_voices[speaker]}")

    # Initialize variables to keep track of timing
    current_time = 0  # in milliseconds
    speaker_timing = {speaker: [] for speaker in speakers}

    # Process each speaker turn and record timing
    for speaker, text in speaker_turns:
        voice = speaker_voices[speaker]

        # Generate filenames with clean speaker names
        segment_index = len(speaker_timing[speaker]) + 1
        clean_speaker_name = re.sub(
            r"[^A-Za-z0-9]", "", speaker
        )  # Remove special characters if needed
        filename = os.path.join(
            current_dir, f"{clean_speaker_name}_segment_{segment_index}.mp3"
        )
        vtt_filename = os.path.join(
            current_dir, f"{clean_speaker_name}_segment_{segment_index}.vtt"
        )

        try:
            await tts(text, voice, filename, vtt_filename)
        except Exception as e:
            logging.error(f"Error creating TTS for {speaker}: {e}")
            continue

        # Load the audio segment
        try:
            audio = AudioSegment.from_file(filename)
            logging.debug(f"Loaded audio for {speaker}, file: {filename}")
        except Exception as e:
            logging.error(f"Error loading audio file {filename}: {e}")
            continue

        # Check if the audio segment is valid
        if not isinstance(audio, AudioSegment):
            logging.error(
                f"Audio for {speaker} is not a valid AudioSegment instance: {audio}"
            )
            continue

        # Record the timing for this segment
        speaker_timing[speaker].append((current_time, audio, vtt_filename))
        logging.debug(
            f"Added timing for {speaker}, current_time: {current_time}, audio duration: {len(audio)} ms"
        )

        # Update current time
        current_time += len(audio)

    # Determine the total duration of the podcast
    total_duration = max(
        [
            start_time + len(audio)
            for timings in speaker_timing.values()
            for (
                start_time,
                audio,
                _,
            ) in timings  # Unpack all three elements, ignore vtt_file
        ]
    )
    # Create empty AudioSegment for each speaker
    speaker_tracks = {}
    for speaker in speakers:
        speaker_tracks[speaker] = AudioSegment.silent(duration=total_duration)

    # Place each audio segment in the correct position on its speaker's track
    for speaker, timings in speaker_timing.items():
        for (
            start_time,
            audio,
            _,
        ) in timings:
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

    # Generate a title, replace spaces with underscores and remove special characters
    title = generate_title(transcript)
    title_ = title.replace(" ", "_")
    clean_title = re.sub(r"[^A-Za-z0-9 ]", "", title_)

    base_file_name, mp3_file, md_file = await get_output_files(output_dir, clean_title)

    # Generate a title, replace spaces with underscores and remove special characters
    write_markdown_file(md_file, f"{title} + \n\n + {transcript}")

    # Create and export the final combined VTT file
    vtt_file = f"{base_file_name}.vtt"
    combine_vtt_files(speaker_timing, vtt_file)

    # Export the final audio to the podcast directory
    combined_audio.export(mp3_file, format="mp3")

    add_mp3_tags(mp3_file, title, img_pth, output_dir)

    # Delete individual audio segments
    for speaker, timings in speaker_timing.items():
        for idx, (start_time, audio, _) in enumerate(timings, start=1):
            filename = os.path.join(current_dir, f"{speaker}_segment_{idx}.mp3")
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    print(f"Deleted segment file: {filename}")
                except Exception as e:
                    print(f"Failed to delete segment file {filename}: {e}")
    logging.info(f"Podcast audio has been generated as '{mp3_file}'.")


def combine_vtt_files(speaker_timing, output_vtt_file):
    """
    Combines individual VTT files into a single VTT file for the podcast.

    Parameters:
    - speaker_timing (dict): A dictionary containing timing and VTT file info for each speaker.
    - output_vtt_file (str): The path to save the combined VTT file.
    """
    combined_subtitles = []
    for speaker, timings in speaker_timing.items():
        for start_time, audio, vtt_file in timings:
            with open(vtt_file, "r", encoding="utf-8") as file:
                vtt_content = file.readlines()

            # Adjust the timing for each subtitle entry based on the start time of the segment
            adjusted_vtt_content = []
            for line in vtt_content:
                if "-->" in line:
                    start, end = line.split(" --> ")
                    start = adjust_timestamp(start, start_time)
                    end = adjust_timestamp(end, start_time)
                    adjusted_vtt_content.append(f"{start} --> {end}\n")
                else:
                    adjusted_vtt_content.append(line)

            combined_subtitles.extend(adjusted_vtt_content)

    # Write combined subtitles to the output VTT file
    with open(output_vtt_file, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")
        file.writelines(combined_subtitles)


def adjust_timestamp(timestamp, offset):
    """
    Adjusts a timestamp by a given offset in milliseconds.

    Parameters:
    - timestamp (str): The original timestamp in 'HH:MM:SS.mmm' format.
    - offset (int): The offset to add in milliseconds.

    Returns:
    - str: The adjusted timestamp.
    """
    time_parts = timestamp.split(":")
    hours, minutes = int(time_parts[0]), int(time_parts[1])
    seconds, milliseconds = map(int, time_parts[2].split("."))
    total_milliseconds = (
        (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds + offset
    )

    new_hours = total_milliseconds // 3600000
    total_milliseconds %= 3600000
    new_minutes = total_milliseconds // 60000
    total_milliseconds %= 60000
    new_seconds = total_milliseconds // 1000
    new_milliseconds = total_milliseconds % 1000

    return f"{new_hours:02}:{new_minutes:02}:{new_seconds:02}.{new_milliseconds:03}"


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
