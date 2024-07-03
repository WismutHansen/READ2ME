import asyncio
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf
import torch
from tqdm import tqdm
import nltk
import numpy as np

# Download the punkt tokenizer for sentence splitting
nltk.download('punkt')

device = "cpu"
if torch.cuda.is_available():
    device = "cuda:0"
elif torch.backends.mps.is_available():
    device = "mps"
elif torch.xpu.is_available():
    device = "xpu"
torch_dtype = torch.float16 if device != "cpu" else torch.float32

model = ParlerTTSForConditionalGeneration.from_pretrained("parler-tts/parler_tts_mini_v0.1").to(device, dtype=torch_dtype)
tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler_tts_mini_v0.1", use_fast=True)

# If setting add_prefix_space, ensure the tokenizer supports it
tokenizer.add_prefix_space = False

async def generate_audio(description, prompt):
    # Split the description into sentences
    sentences = nltk.sent_tokenize(description)

    # Prepare the prompt input
    prompt_input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)

    # Generate audio for each sentence
    audio_segments = []

    for sentence in tqdm(sentences, desc="Generating audio"):
        input_ids = tokenizer(sentence, return_tensors="pt").input_ids.to(device)
        
        generation = model.generate(
            input_ids=input_ids, 
            prompt_input_ids=prompt_input_ids
        ).to(torch.float32)
        
        audio_arr = generation.cpu().numpy().squeeze()
        audio_segments.append(audio_arr)

    # Concatenate all audio segments
    full_audio = np.concatenate(audio_segments)

    return full_audio

if __name__ == "__main__":
    print("Welcome to the Parler TTS Generator!")
    
    # Get user input for the description
    prompt = input("Please enter the text you want to convert to speech: ")
    
    # You can modify this prompt or even ask the user to input it
    description = "A female speaker with a slightly low-pitched voice delivers her words quite expressively, in a very confined sounding environment with clear audio quality. She speaks very fast."
    
    print("\nGenerating audio... This may take a while depending on the length of your text.")
    
    # Run the async function
    full_audio = asyncio.run(generate_audio(description, prompt))
    
    # Write the full audio to a file
    output_file = "parler_tts_out.wav"
    sf.write(output_file, full_audio, model.config.sampling_rate)
    
    print(f"\nAudio generation complete! The output has been saved to {output_file}")