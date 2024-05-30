import subprocess
import os

def piper_say(text):
    command = (
        f'echo "{text}" | '
        "piper --model /Users/tommyfalkowski/Code/READ2ME/utils/piper/models/en_GB-cori-high.onnx "
        "--length-scale 0.9 --output_file Output/welcome.wav"
    )

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("Command output:", result.stdout)
        print("Command error (if any):", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit status {e.returncode}")
        print("Error output:", e.stderr)

if __name__ == "__main__":
    piper_say("Hello, I am READ2ME")