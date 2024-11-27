import outetts
import os
from utils.common_utils import download_file

directory = "TTS/OuteTTS/models/"
file_extension = ".gguf"
file_url = "https://huggingface.co/OuteAI/OuteTTS-0.2-500M-GGUF/resolve/main/OuteTTS-0.2-500M-Q6_K.gguf"
destination_file = None

# Find existing .gguf file
for file in os.listdir(directory):
    if file.endswith(file_extension):
        destination_file = os.path.join(directory, file)
        print(f"Existing .gguf file found: {destination_file}")
        break

# If no .gguf file is found, download the file
if destination_file is None:
    print("No .gguf file found. Downloading...")
    destination_file = os.path.join(directory, "OuteTTS-0.2-500M-Q6_K.gguf")
    download_file(file_url, destination_file)
    print(f"File downloaded to {destination_file}")
# Configure the model
model_config = outetts.GGUFModelConfig_v1(
    model_path="OuteTTS/models/OuteTTS-0.2-500M-Q6_K.gguf",
    language="en",
    n_gpu_layers=-1,
)

# Initialize the interface
interface = outetts.InterfaceGGUF(model_version="0.2", cfg=model_config)

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
