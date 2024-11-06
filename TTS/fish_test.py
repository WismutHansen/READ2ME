import asyncio
from .tts_engines import FishTTSEngine

# Adjust these paths as needed
MODEL_REPO = "fishaudio/fish-speech-1.4"
VOICES_DIR = "TTS/voices"

# Create an instance of FishTTSEngine
fish_tts_engine = FishTTSEngine(
    model_repo=MODEL_REPO,
    voices_dir=VOICES_DIR,
)


# Test function to generate audio
async def test_generate_audio(engine, text, output_file="test_output.wav"):
    try:
        voices = await engine.get_available_voices()
        voice_id = await engine.pick_random_voice(voices)
        print(f"Testing FishTTSEngine with voice: {voice_id}")
        audio_segment, _ = await engine.generate_audio(text, voice_id)

        # Check if audio_segment is not None and has data
        if audio_segment is not None:
            print(f"Audio segment duration: {len(audio_segment)} milliseconds")
            if len(audio_segment) > 0:
                # Save audio to output file
                audio_segment.export(output_file, format="wav")
                print(f"Audio generated and saved to {output_file}")
            else:
                print("Audio segment is empty.")
        else:
            print("No audio segment returned.")
    except Exception as e:
        print(f"Error during audio generation: {e}")


# Main script to test FishTTSEngine
if __name__ == "__main__":
    sample_text = "Hello, this is a test of the Fish TTS engine."

    # Run the test
    asyncio.run(test_generate_audio(fish_tts_engine, sample_text))
