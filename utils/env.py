#!/usr/bin/env python3
# env.py
# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
import logging
import shutil

from dotenv.main import DotEnv


def setup_env() -> tuple[str, str, str, str]:
    """
    Sets up the environment for the application by ensuring required files exist,
    copying default configurations if necessary, and loading environment variables.

    Returns:
        tuple[str, str, str, str]: A tuple containing:
            - output_dir (str): The output directory path.
            - task_file (str): The path to the tasks JSON file.
            - img_pth (str): The path to the album art image.
            - sources_file_path (str): The path to the sources JSON file.
    """
    task_file: str = "tasks.json"
    sources_file_path: str = "sources.json"
    feeds_file: str = "feeds.json"
    personal_feeds: str = "my_feeds.json"
    env_example: str = ".env.example"
    env_file: str = ".env"

    if not os.path.isfile(task_file):
        print("Creating tasks.json")
        with open(task_file, "w") as f:
            pass  # Creates an empty tasks.json file

    if not os.path.isfile(personal_feeds):
        print("my_feeds.json does not exist, copying feeds.json to my_feeds.json")
        shutil.copyfile(feeds_file, personal_feeds)

    if not os.path.isfile(env_file):
        print(".env file does not exist, copying .env.example to .env")
        shutil.copyfile(env_example, env_file)

    if not os.path.isfile(sources_file_path):
        print("Creating sources.json")
        with open(sources_file_path, "w") as f:
            pass  # Creates an empty sources.json file

    load_dotenv()
    output_dir: str = os.getenv("OUTPUT_DIR", "Output")
    img_pth: str = os.getenv("IMG_PATH", "front.jpg")

    check_output_dir()  # Ensure the output directory exists (assuming the function exists)

    logging.info("Setup complete, following values will be used:")
    logging.info("Output folder: %s", os.path.abspath(output_dir))
    logging.info("Task file: %s", os.path.abspath(task_file))
    logging.info("Album Art Image: %s", os.path.abspath(img_pth))
    logging.info("Sources file: %s", os.path.abspath(sources_file_path))

    return output_dir, task_file, img_pth, sources_file_path


def check_output_dir() -> str:
    """
    Ensures that the OUTPUT_DIR specified in the .env file exists.
    If the directory does not exist, it creates it.

    Returns:
        str: The absolute path to the OUTPUT_DIR.

    Raises:
        ValueError: If the directory creation fails due to an OS error.
    """
    load_dotenv()

    output_folder: str = os.getenv("OUTPUT_DIR", "Output")

    # Check if the output folder exists; create it if necessary
    if not os.path.exists(output_folder):
        print(f"Output folder '{output_folder}' does not exist. Creating it...")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Failed to create OUTPUT_DIR: {e}")

    return os.path.abspath(output_folder)


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
