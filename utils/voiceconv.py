import os
import torch
from rvc_python.infer import RVCInference
from .common_utils import convert_wav_to_mp3
import logging


def voice2voice(
    input_file_path: str, output_dir: str, base_file_name: str, model_name: str
):
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Use absolute paths relative to the script's location
    model_dir = os.path.join(script_dir, "rvc/Models/")
    model_path = os.path.join(
        script_dir, "rvc/Models/", model_name, model_name + ".pth"
    )
    index_path = os.path.join(
        script_dir, "rvc/Models/", model_name, model_name + ".index"
    )

    if os.path.isfile(model_path):
        # Check if index file exists
        index_path = index_path if os.path.isfile(index_path) else None
        backend = "cuda:0" if torch.cuda.is_available() else "cpu"

        rvc_file = os.path.join(output_dir, f"{base_file_name}_rvc.wav")
        output_file = os.path.join(output_dir, f"{base_file_name}.mp3")

        rvc = RVCInference(device=backend)
        rvc.set_models_dir(model_dir)
        rvc.load_model(model_name)
        rvc.set_params(f0method="rmvpe", f0up_key=0, index_path=index_path)
        rvc.infer_file(input_path=input_file_path, output_path=rvc_file)

        mp3 = convert_wav_to_mp3(wav_file=rvc_file, mp3_file=output_file)
        return mp3
    else:
        logging.error(
            f"RVC conversion failed: Model checkpoint not found at {model_path}."
        )
        return None


def main(file: str, output_dir: str, model: str):
    try:
        voice2voice(file, output_dir, "test", model)
        print(f"File saved in {output_dir}")
    except Exception as e:
        print(f"Voice conversion failed: {e}")


if __name__ == "__main__":
    file = "test.mp3"
    output_dir = "test"
    model = "Female_1"
    main(file, output_dir, model)
