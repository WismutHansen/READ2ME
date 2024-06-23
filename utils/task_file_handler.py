import os
import aiofiles
import logging
from utils.env import setup_env

output_dir, task_file, img_pth, sources_file, keywords_file = setup_env()

async def add_task(task_type, content, tts_engine):
    task = f"{task_type},{content},{tts_engine}\n"
    logging.info(f"Adding task: {task.strip()}")
    try:
        async with aiofiles.open(task_file, "a") as file:
            await file.write(task)
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

        # Filter out any empty lines or lines that do not have the correct format
        valid_tasks = [
            task.strip().split(",") for task in tasks if len(task.strip().split(",")) == 3
        ]
        if len(valid_tasks) > 0:
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
                await file.write(f"{','.join(task)}\n")
        
        logging.info(f"Task removed from {task_file}")
    except IOError as e:
        logging.error(f"Error removing task from {task_file}: {e}")
        raise

async def get_task_count():
    tasks = await get_tasks()
    return len(tasks)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
