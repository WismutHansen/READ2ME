import asyncio
import edge_tts

async def update_voice_list():
    """
    Fetches the list of available voices from edge_tts and saves them to 'edge_voices.txt'.
    """
    voices_manager = await edge_tts.VoicesManager.create()
    voices = voices_manager.voices

    with open("edge_voices.txt", "w", encoding="utf-8") as f:
        for voice in voices:
            f.write(f"Name: {voice['Name']}\n")
            f.write(f"ShortName: {voice['ShortName']}\n")
            f.write(f"Gender: {voice['Gender']}\n")
            f.write(f"Locale: {voice['Locale']}\n")
            f.write(f"SampleRateHertz: {voice.get('SampleRateHertz', '')}\n")
            f.write(f"VoiceType: {voice.get('VoiceType', '')}\n")
            f.write(f"Status: {voice.get('Status', '')}\n")
            f.write(f"StyleList: {', '.join(voice.get('StyleList', []))}\n")
            f.write(f"RolePlayList: {', '.join(voice.get('RolePlayList', []))}\n")
            f.write(f"VoiceTag: {voice.get('VoiceTag', '')}\n")
            f.write("-" * 50 + "\n")
    print("Voice list has been updated and saved to 'edge_voices.txt'.")

if __name__ == "__main__":
    asyncio.run(update_voice_list())
