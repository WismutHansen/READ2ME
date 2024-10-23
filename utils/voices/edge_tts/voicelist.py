import asyncio
import logging
from edge_tts import VoicesManager


async def amain() -> None:
    voices = await VoicesManager.create()
    en_us_voices = [
        voice
        for voice in voices.voices
        if "en-US" in voice["Name"]
        and ("MultilingualNeural" in voice["Name"] or "Neural" in voice["Name"])
    ]
    if not en_us_voices:
        logging.error("No en-US MultilingualNeural or en-US Neural voices found")
        return None, None, None  # Instead of raising an exception, return None
    for voice in en_us_voices:
        print(voice["Name"])


if __name__ == "__main__":
    asyncio.run(amain())
