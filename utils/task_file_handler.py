import os
import aiofiles
import logging
import json
from utils.env import setup_env
from typing import Union, List, Dict, Any

output_dir, task_file, img_pth, sources_file = setup_env()


async def load_tasks() -> List[Dict[str, Any]]:
    """
    Loads all tasks from the task file. If the file is empty or invalid, it returns an empty list.

    Returns:
        List[Dict[str, Any]]: A list of task dictionaries.
    """
    if not os.path.exists(task_file) or os.path.getsize(task_file) == 0:
        return []

    try:
        async with aiofiles.open(task_file, "r", encoding="utf-8") as file:
            content = await file.read()
            if not content.strip():
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to read {task_file}: {e}")
        return []


async def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """
    Saves a list of tasks to the task file, ensuring proper JSON formatting.

    Args:
        tasks (List[Dict[str, Any]]): The list of tasks to save.
    """
    try:
        async with aiofiles.open(task_file, "w", encoding="utf-8") as file:
            await file.write(json.dumps(tasks, indent=2))  # Pretty-print JSON
    except IOError as e:
        logging.error(f"Error writing tasks to {task_file}: {e}")
        raise


async def add_task(
    task_type: str, content: str, tts_engine: str, task: Union[str, dict, None] = None
) -> None:
    """
    Adds a new task to the task queue.

    Args:
        task_type (str): The type of task.
        content (str): The content related to the task.
        tts_engine (str): The TTS engine to use.
        task (Union[str, dict, None], optional): Additional task metadata.
    """
    new_task = {
        "type": task_type,
        "content": content,
        "tts_engine": tts_engine,
        "task": task if isinstance(task, str) else None,
    }

    tasks = await load_tasks()
    tasks.append(new_task)
    await save_tasks(tasks)

    logging.info(f"Task added: {json.dumps(new_task)}")


async def get_tasks() -> List[Dict[str, Any]]:
    """
    Retrieves all tasks from the task file.

    Returns:
        List[Dict[str, Any]]: A list of tasks.
    """
    tasks = await load_tasks()
    logging.debug(f"Retrieved {len(tasks)} tasks from {task_file}")
    return tasks


async def clear_tasks() -> None:
    """
    Clears all tasks from the task queue.
    """
    await save_tasks([])  # Save an empty JSON array
    logging.info(f"Tasks cleared from {task_file}")


async def remove_task(task_to_remove: Dict[str, Any]) -> None:
    """
    Removes a specific task from the task queue.

    Args:
        task_to_remove (Dict[str, Any]): The task dictionary to remove.
    """
    tasks = await load_tasks()
    tasks = [task for task in tasks if task != task_to_remove]
    await save_tasks(tasks)

    logging.info(f"Task removed from {task_file}")


async def get_task_count() -> int:
    """
    Gets the count of tasks in the queue.

    Returns:
        int: The number of tasks in the queue.
    """
    tasks = await load_tasks()
    return len(tasks)


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
