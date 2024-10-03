import os
import random
from pydub import AudioSegment

def parse_transcript(transcript):
    """
    Parses the transcript into a list of (speaker, text) tuples.
    """
    speaker_turns = []
    lines = transcript.strip().split('\n')
    for line in lines:
        if ':' in line:
            speaker, text = line.split(':', 1)
            speaker = speaker.strip()
            text = text.strip()
            speaker_turns.append((speaker, text))
    return speaker_turns

def create_podcast_audio(transcript: str, tts_engine: str, voice_1: str = None, voice_2: str = None):
    """
    Creates the podcast audio from the transcript.
    """
    # Parse the transcript
    speaker_turns = parse_transcript(transcript)

    # Identify speakers and assign voices and numbering
    speakers = {}
    speaker_voices = {}
    file_counter = 1

    # Assign odd and even numbers and voices to speakers
    for speaker, _ in speaker_turns:
        if speaker not in speakers:
            if len(speakers) == 0:
                speakers[speaker] = 1  # Speaker 1: odd numbers
                speaker_voices[speaker] = 'voice1'  # Replace with actual voice identifiers
            else:
                speakers[speaker] = 2  # Speaker 2: even numbers
                speaker_voices[speaker] = 'voice2'

    # Process each speaker turn
    audio_segments = []
    segment_number = 1

    for speaker, text in speaker_turns:
        voice = speaker_voices[speaker]
        # Determine the filename
        if speakers[speaker] == 1:
            # Speaker 1: odd numbers
            filename = f"{segment_number * 2 - 1}.mp3"
        else:
            # Speaker 2: even numbers
            filename = f"{segment_number * 2}.mp3"

        # Generate the audio file using the TTS function
        tts(text, voice, filename)  # Assuming tts saves audio to filename

        # Load the audio segment
        audio = AudioSegment.from_file(filename)

        # Pan the audio
        if speakers[speaker] == 1:
            # Speaker 1, pan slightly to the left
            audio = audio.pan(-0.3)
        else:
            # Speaker 2, pan slightly to the right
            audio = audio.pan(0.3)

        # Add the audio segment to the list
        audio_segments.append(audio)
        segment_number += 1

    # Combine the audio segments with random overlaps
    combined_audio = AudioSegment.silent(duration=0)
    current_position = 0  # in milliseconds

    for audio in audio_segments:
        # Determine overlap in milliseconds (-200 ms to 500 ms)
        overlap = random.randint(-200, 500)

        if overlap < 0:
            # Overlap with the previous segment
            start_time = current_position + overlap
            if start_time < 0:
                # Pad the beginning with silence if necessary
                combined_audio = AudioSegment.silent(duration=-start_time).append(combined_audio)
                start_time = 0
                current_position = 0
            combined_audio = combined_audio.overlay(audio, position=start_time)
            current_position = max(current_position, start_time + len(audio))
        else:
            # Gap between segments
            current_position += overlap
            combined_audio = combined_audio.overlay(audio, position=current_position)
            current_position += len(audio)

    # Add 1 second of padding at the end
    combined_audio += AudioSegment.silent(duration=1000)

    # Export the final audio
    combined_audio.export("podcast.mp3", format="mp3")
    print("Podcast audio has been generated as 'podcast.mp3'.")

# Mock TTS function (replace this with your actual TTS implementation)
def tts(text, voice, filename):
    """
    Mock TTS function that generates silent audio proportional to the text length.
    Replace this function with your actual TTS implementation.
    """
    # For demonstration, create silence proportional to text length
    duration = len(text) * 50  # 50 ms per character (adjust as needed)
    audio = AudioSegment.silent(duration=duration)
    audio.export(filename, format="mp3")

# Example usage
if __name__ == "__main__":
    transcript = """
    Alex: Hey, did you hear about the new Python release?
    Taylor: Oh, um, no, I haven't. What's new in it?
    Alex: Well, they added some, you know, really cool features like pattern matching.
    Taylor: That's awesome! I was waiting for that feature.
    """
    create_podcast_audio(transcript)
