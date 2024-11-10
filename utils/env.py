import os
from dotenv import load_dotenv
import logging
import shutil

from dotenv.main import DotEnv


def setup_env():
    task_file = "tasks.json"
    sources_file_path = "sources.json"
    feeds_file = "feeds.json"
    personal_feeds = "my_feeds.json"
    env_example = ".env.example"
    env_file = ".env"

    if not os.path.isfile(task_file):
        print("Creating tasks.json")
        with open(task_file, "w") as f:
            pass  # This creates an empty tasks.json file

    if not os.path.isfile(personal_feeds):
        print("my_feeds.json does not exist, copying feeds.json to my_feeds.json")
        shutil.copyfile(feeds_file, personal_feeds)

    if not os.path.isfile(env_file):
        print(".env file does not exist, copying .env.example to .env")
        shutil.copyfile(env_example, env_file)

    if not os.path.isfile(sources_file_path):
        print("Creating sources.json")
        with open(sources_file_path, "w") as f:
            pass  # This creates an empty sources.txt file

    load_dotenv()
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    img_pth = os.getenv("IMG_PATH", "front.jpg")

    check_output_dir()

    logging.info("Setup complete, following values will be used:")
    logging.info("Output folder: " + os.path.abspath(output_dir))
    logging.info("Task file: " + os.path.abspath(task_file))
    logging.info("Album Art Image: " + os.path.abspath(img_pth))
    logging.info("Sources file: " + os.path.abspath(sources_file_path))

    return output_dir, task_file, img_pth, sources_file_path


def check_output_dir():
    """
    Checks if the OUTPUT_FOLDER specified in .env exists.
    Creates it if not.

    Returns:
        str: The path to the OUTPUT_FOLDER.
    """
    load_dotenv()

    output_folder = os.getenv("OUTPUT_DIR", "Output")

    # Check if the output folder exists
    if not os.path.exists(output_folder):
        print(f"Output folder '{output_folder}' does not exist. Creating it...")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Failed to create OUTPUT_FOLDER: {e}")

    return output_folder


def print_env_contents():
    env_path = ".env"
    if os.path.isfile(env_path):
        print("Contents of .env file:")
        with open(env_path, "r") as f:
            print(f.read())
    else:
        print(".env file not found")


if __name__ == "__main__":
    output_dir, task_file, img_pth, sources_file_path = setup_env()
    print_env_contents()
    print("Setup complete, following values will be used:")
    print("Output folder: " + os.path.abspath(output_dir))
    print("Task file: " + os.path.abspath(task_file))
    print("Album Art Image: " + os.path.abspath(img_pth))
    print("Sources file: " + os.path.abspath(sources_file_path))
