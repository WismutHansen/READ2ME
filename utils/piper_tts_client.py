import os
import subprocess
import utils
import platform
from .common_utils import strip_markdown


class PiperTTSClient:
    def __init__(self, verbose=False):
        """Initialize the Piper TTS client."""
        self.verbose = verbose

    def tts(self, text_to_speak, output_file, voice_folder):
        """
        This function uses the Piper TTS engine to convert text to speech.
        
        Args:
            text_to_speak (str): The text to be converted to speech.
            output_file (str): The path where the output audio file will be saved.
            voice_folder (str): The folder containing the voice files for the TTS engine.
            
        Returns:
            str: "success" if the TTS process was successful, "failed" otherwise.
        """


        # Sanitize the text to be spoken
        text_to_speak = strip_markdown(text_to_speak)

        # If there's no text left after sanitization, return "failed"
        if not text_to_speak.strip():
            if self.verbose:
                print("No text to speak after sanitization.")
            return "failed"

        # Determine the operating system
        operating_system = platform.system()
        script_folder = os.path.dirname(os.path.abspath(__file__))
        if operating_system == "Windows":
            piper_binary = os.path.join(script_folder, "piper_tts", "piper.exe")
        else:
            piper_binary = os.path.join(script_folder, "piper_tts", "piper")

        # Construct the path to the voice files
        voice_path = os.path.join(script_folder, "piper_tts", "voices", voice_folder)

        # If the voice folder doesn't exist, return "failed"
        if not os.path.exists(voice_path):
            if self.verbose:
                print(f"Voice folder '{voice_folder}' does not exist.")
            return "failed"

        # Find the model and JSON files in the voice folder
        files = os.listdir(voice_path)
        model_path = next((os.path.join(voice_path, f) for f in files if f.endswith('.onnx')), None)
        json_path = next((os.path.join(voice_path, f) for f in files if f.endswith('.json')), None)

        # If either the model or JSON file is missing, return "failed"
        if not model_path or not json_path:
            if self.verbose:
                print("Required voice files not found.")
            return "failed"
        
        PIPER_VOICE_INDEX = 0 # For multi-voice models, select the index of the voice you want to use
        PIPER_VOICE_SPEED = 0.8 # Speed of the TTS, 1.0 is normal speed, 2.0 is double speed, 0.5 is half speed

        try:
            # Construct and execute the Piper TTS command
            command = [
                piper_binary,
                "-m", model_path,
                "-c", json_path,
                "-f", output_file,
                "-s", str(PIPER_VOICE_INDEX),
                "--length_scale", str(1/PIPER_VOICE_SPEED)
            ]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=(None if self.verbose else subprocess.DEVNULL), stderr=subprocess.STDOUT)
            process.communicate(text_to_speak.encode("utf-8"))
            process.wait()
            if self.verbose:
                print(f"Piper TTS command executed successfully.")
            return "success"
        except subprocess.CalledProcessError as e:
            # If the command fails, print an error message and return "failed"
            if self.verbose:
                print(f"Error running Piper TTS command: {e}")
            return "failed"
        
if __name__ == "__main__":

    text_to_speak = input("Please enter the text you want to convert to speech: ")
    
    script_folder = os.path.dirname(os.path.abspath(__file__))
    voice_folder = "default_female_voice/"
    output_file = os.path.join(script_folder, "output.wav")

    tts_client = PiperTTSClient(verbose=True)
    result = tts_client.tts(text_to_speak, output_file, voice_folder)

    if result == "success":
        print(f"Speech synthesis successful. The output file is saved at: {output_file}")
    else:
        print("Speech synthesis failed.")