import asyncio
from .tts_engines import FishTTSEngine
import torch

# Adjust these paths as needed
MODEL_REPO = "fishaudio/fish-speech-1.4"  # Example Hugging Face model repository
DECODER_REPO = "fishaudio/fish-speech-1.4"  # Example decoder model repository
VOICES_DIR = "TTS/voices"  # Directory containing .wav reference voices

# Create an instance of FishTTSEngine
fish_tts_engine = FishTTSEngine(
    model_repo=MODEL_REPO,
    decoder_repo=DECODER_REPO,
    voices_dir=VOICES_DIR,
    device="cuda" if torch.cuda.is_available() else "cpu",
)


# Test function to generate audio
async def test_generate_audio(engine, text, voice_id, output_file="test_output.wav"):
    try:
        print(f"Testing FishTTSEngine with voice: {voice_id}")
        audio_segment, _ = await engine.generate_audio(text, voice_id)

        # Save audio to output file
        if audio_segment:
            audio_segment.export(output_file, format="wav")
            print(f"Audio generated and saved to {output_file}")
        else:
            print("No audio segment returned.")
    except Exception as e:
        print(f"Error during audio generation: {e}")


# Main script to test FishTTSEngine
if __name__ == "__main__":
    # Sample text and voice_id (use one of the available .wav filenames in VOICES_DIR without the .wav extension)
    sample_text = "Hello, this is a test of the Fish TTS engine."
    sample_voice_id = (
        "sample_voice"  # Replace with an actual voice ID from your voices directory
    )

    # Run the test
    asyncio.run(test_generate_audio(fish_tts_engine, sample_text, sample_voice_id))
