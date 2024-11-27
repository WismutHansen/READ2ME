import outetts

# Configure the model
model_config = outetts.HFModelConfig_v1(
    model_path="OuteAI/OuteTTS-0.2-500M",
    language="en",  # Supported languages in v0.2: en, zh, ja, ko
)

# Initialize the interface
interface = outetts.InterfaceHF(model_version="0.2", cfg=model_config)

# Optional: Create a speaker profile (use a 10-15 second audio clip)
# speaker = interface.create_speaker(
#     audio_path="path/to/audio/file",
#     transcript="Transcription of the audio file."
# )

# Optional: Save and load speaker profiles
# interface.save_speaker(speaker, "speaker.json")
# speaker = interface.load_speaker("speaker.json")

# Optional: Load speaker from default presets
interface.print_default_speakers()
speaker = interface.load_default_speaker(name="male_2")

output = interface.generate(
    text="Speech synthesis is the artificial production of human speech. A computer system used for this purpose is called a speech synthesizer, and it can be implemented in software or hardware products.",
    # Lower temperature values may result in a more stable tone,
    # while higher values can introduce varied and expressive speech
    temperature=0.1,
    repetition_penalty=1.1,
    max_length=4096,
    # Optional: Use a speaker profile for consistent voice characteristics
    # Without a speaker profile, the model will generate a voice with random characteristics
    speaker=speaker,
)

# Save the synthesized speech to a file
output.save("output.wav")

# Optional: Play the synthesized speech
# output.play()
