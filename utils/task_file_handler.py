import os
import aiofiles
import logging
import json
from utils.env import setup_env
from typing import Union

output_dir, task_file, img_pth, sources_file = setup_env()


async def add_task(
    task_type: str, content: str, tts_engine: str, task: Union[str, dict, None] = None
):
    task = {
        "type": task_type,
        "content": content,
        "tts_engine": tts_engine,
        "task": task if isinstance(task, str) else None,
    }
    task_json = json.dumps(task)
    logging.info(f"Adding task: {task_json}")
    try:
        async with aiofiles.open(task_file, "a") as file:
            await file.write(task_json + "\n")
        logging.info(f"Task added to {task_file}")
    except IOError as e:
        logging.error(f"Error adding task to {task_file}: {e}")
        raise


async def get_tasks():
    if not os.path.exists(task_file):
        logging.warning(f"Task file {task_file} does not exist.")
        return []

    try:
        async with aiofiles.open(task_file, "r") as file:
            tasks = await file.readlines()

        valid_tasks = []
        for task in tasks:
            try:
                task_dict = json.loads(task.strip())
                if all(key in task_dict for key in ["type", "content", "tts_engine"]):
                    valid_tasks.append(task_dict)
            except json.JSONDecodeError:
                logging.warning(f"Invalid task format: {task}")

        if valid_tasks:
            logging.info(f"Retrieved {len(valid_tasks)} valid tasks from {task_file}")
        return valid_tasks
    except IOError as e:
        logging.error(f"Error reading tasks from {task_file}: {e}")
        raise


async def clear_tasks():
    try:
        async with aiofiles.open(task_file, "w") as file:
            await file.write("")
        logging.info(f"Tasks cleared from {task_file}")
    except IOError as e:
        logging.error(f"Error clearing tasks from {task_file}: {e}")
        raise


async def remove_task(task_to_remove):
    try:
        tasks = await get_tasks()
        tasks = [task for task in tasks if task != task_to_remove]

        async with aiofiles.open(task_file, "w") as file:
            for task in tasks:
                await file.write(json.dumps(task) + "\n")

        logging.info(f"Task removed from {task_file}")
    except IOError as e:
        logging.error(f"Error removing task from {task_file}: {e}")
        raise


async def get_task_count():
    tasks = await get_tasks()
    return len(tasks)


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

