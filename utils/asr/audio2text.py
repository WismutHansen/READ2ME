import torch
from transformers import pipeline

MODEL_NAME = "ylacombe/whisper-large-v3-turbo"
BATCH_SIZE = 8

device = 0 if torch.cuda.is_available() else "cpu"

pipe = pipeline(
    task="automatic-speech-recognition",
    model=MODEL_NAME,
    chunk_length_s=30,
    device=device,
)


def transcribe(inputs):
    text = pipe(inputs, batch_size=BATCH_SIZE, return_timestamps=True)
    return text


def convert_to_vtt(transcription, output_file):
    # Start the .vtt file with the proper header
    vtt_content = "WEBVTT\n\n"

    # Iterate over the chunks in the input data to add each line
    for idx, chunk in enumerate(transcription["chunks"]):
        start, end = chunk["timestamp"]
        text = chunk["text"]

        # Convert timestamps from seconds to WebVTT format
        start_vtt = convert_to_vtt_timestamp(start)
        end_vtt = convert_to_vtt_timestamp(end)

        # Format the output to be compatible with VTT files
        vtt_content += f"{idx + 1}\n{start_vtt} --> {end_vtt}\n{text}\n\n"

    # Save the VTT content to a file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    print("Conversion completed. File saved as output.vtt.")


def convert_to_vtt_timestamp(seconds):
    # Convert seconds into the VTT time format (hh:mm:ss.mmm)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


if __name__ == "__main__":
    inputs = input("Please enter the path to an audio file: ")
    text = transcribe(inputs)
    print(text)
