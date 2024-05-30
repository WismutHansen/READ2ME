import os
from utils.env import setup_env

output_dir, task_file, img_pth = setup_env()


def add_task(task_type, content, tts_engine):
    task = f"{task_type},{content},{tts_engine}\n"
    print(f"Adding task: {task}")  # Debug statement
    with open(task_file, "a") as file:
        file.write(task)
    print(f"Task added to {task_file}")


def get_tasks():
    if not os.path.exists(task_file):
        return []

    with open(task_file, "r") as file:
        tasks = file.readlines()

    # Filter out any empty lines or lines that do not have the correct format
    valid_tasks = [
        task.strip().split(",") for task in tasks if len(task.strip().split(",")) == 3
    ]

    return valid_tasks


def clear_tasks():
    with open(task_file, "w") as file:
        file.write("")
    print(f"Tasks cleared from {task_file}")  # Debug statement
