from .tts_engines import EdgeTTSEngine, F5TTSEngine
from .tts_functions import PodcastGenerator
import asyncio


async def podcast_edge(transcript: str):
    # Using Edge TTS
    edge_tts = EdgeTTSEngine()
    podcast_gen = PodcastGenerator(edge_tts)
    return await podcast_gen.create_podcast_audio(transcript)


async def podcast_F5(transcript: str):
    # Using F5 TTS
    f5_tts = F5TTSEngine("utils/voices/")
    podcast_gen = PodcastGenerator(f5_tts)
    await podcast_gen.create_podcast_audio(transcript)


if __name__ == "__main__":
    transcript = """
    speaker1: Hello, this is a test of the podcast generation system.
    speaker2: Yes, we're testing if the audio generation works properly.
    speaker1: Let's make sure all the timing and transitions are smooth.
    """
    asyncio.run(podcast_F5(transcript))
