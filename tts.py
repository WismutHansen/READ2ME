import argparse
import torch
import numpy as np
from scipy.io.wavfile import write
import ljspeechimportable
from txtsplit import txtsplit
import sounddevice as sd

from tqdm import tqdm

def ljsynthesize(text, steps):
    sr =24000
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    noise = torch.randn(1,1,256).to(device)
    if text.strip() == "":
        raise ValueError("You must enter some text")
    if len(text) > 150000:
        raise ValueError("Text must be <150k characters")
    #print("*** saying ***")
    #print(text)
    #print("*** end ***")
    texts = txtsplit(text)
    audios = []
    for t in tqdm(texts, desc="Synthesizing"):
                audios.append(ljspeechimportable.inference(t, noise, diffusion_steps=steps, embedding_scale=1))
    full_audio = np.concatenate(audios)

    # Audio EQ - Low-pass filter
    cutoff_freq = 7000  # Cutoff frequency in Hz
    fs = 24000  # Sampling frequency in Hz
    order = 6  # Order of the filter
    b, a = scipy.signal.butter(order, cutoff_freq / (0.5 * fs), btype='low')
    filtered_audio = scipy.signal.filtfilt(b, a, full_audio)

    return (fs, filtered_audio)

def main():
    parser = argparse.ArgumentParser(description='LJSpeech TTS CLI')
    parser.add_argument('text', type=str, help='Input text to synthesize')
    parser.add_argument('--steps', type=int, default=3, help='Number of diffusion steps (default: 3)')
    parser.add_argument('--output', type=str, help='Output WAV file name')
    args = parser.parse_args()

    sample_rate, audio = ljsynthesize(args.text, args.steps)
    print("Playing audio...")
    sd.play(audio, samplerate=sample_rate)
    sd.wait()

    if args.output:
        write(args.output, sample_rate, audio)
        print(f"Audio saved as {args.output}")

if __name__ == "__main__":
    main()