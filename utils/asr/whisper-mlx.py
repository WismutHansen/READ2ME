import os
import mlx_whisper


def transcribe_directory(audio_dir, model="mlx-community/whisper-large-v3-mlx"):
    # Create the output directory if it doesn't exist
    if not os.path.exists(audio_dir):
        print("output dir does not exit")
        return False

    # Iterate through all files in the audio directory
    for file_name in os.listdir(audio_dir):
        file_path = os.path.join(audio_dir, file_name)

        # Check if it's an audio file (add more extensions as needed)
        if file_name.lower().endswith((".mp3", ".wav", ".flac", ".m4a")):
            try:
                # Transcribe the audio file using the specified model
                result = mlx_whisper.transcribe(file_path, path_or_hf_repo=model)

                # Extract the transcription text
                text = result.get("text", "")

                # Create a corresponding text file for the transcription
                output_file_path = os.path.join(
                    audio_dir, f"{os.path.splitext(file_name)[0]}.txt"
                )

                # Write the transcription to the text file
                with open(output_file_path, "w") as text_file:
                    text_file.write(text)

                print(f"Transcription saved for {file_name}")
            except Exception as e:
                print(f"Error transcribing {file_name}: {e}")


if __name__ == "__main__":
    audio_directory = input(
        "Please enter a directory path: "
    )  # Replace with your audio directory path
    transcribe_directory(audio_directory)
