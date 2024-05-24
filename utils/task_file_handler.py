import os

# Define the task file path relative to the parent directory of "utils"
TASK_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tasks.txt')

def add_task(task_type, content, tts_engine):
    task = f"{task_type},{content},{tts_engine}\n"
    print(f"Adding task: {task}")  # Debug statement
    with open(TASK_FILE, 'a') as file:
        file.write(task)
    print(f"Task added to {TASK_FILE}")

def get_tasks():
    if not os.path.exists(TASK_FILE):
        return []

    with open(TASK_FILE, 'r') as file:
        tasks = file.readlines()

    # Filter out any empty lines or lines that do not have the correct format
    valid_tasks = [task.strip().split(',') for task in tasks if len(task.strip().split(',')) == 3]

    return valid_tasks

def clear_tasks():
    with open(TASK_FILE, 'w') as file:
        file.write("")
    print(f"Tasks cleared from {TASK_FILE}")  # Debug statement