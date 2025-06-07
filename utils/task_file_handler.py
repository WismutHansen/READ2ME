#!/usr/bin/env python3
# task_file_handler.py
# -*- coding: utf-8 -*-
import os
import aiofiles
import logging
import json
from utils.env import setup_env
from typing import Union, List, Dict, Any
import time
import random
import string
from utils.common_enums import TaskStatus, InputType, TaskType
from datetime import datetime

output_dir, task_file, img_pth, sources_file = setup_env()


def generate_task_id(length: int = 6) -> str:
    timestamp = int(time.time())  # current time in seconds
    # A quick random 6-char string (no re-seeding)
    rand_part = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )
    return f"{timestamp}-{rand_part}"


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
    input_type: InputType, content: str, tts_engine: str, task_type: TaskType
) -> str:
    """
    Adds a new task to the task queue.

    Args:
        input_type (InputType): The type of the Input either url or text.
        content (str): The content related to the task.
        tts_engine (str): The TTS engine to use.
        task_type (TaskType): Additional task metadata.

    Returns:
        str: The ID of the added task.
    """
    task_id = generate_task_id()
    
    # Convert enums to their string values for JSON serialization
    task = {
        "id": task_id,
        "type": input_type.value if hasattr(input_type, 'value') else str(input_type),
        "content": content,
        "tts_engine": tts_engine,
        "task": task_type.value if hasattr(task_type, 'value') else str(task_type),
        "status": TaskStatus.PENDING.value,  # Use enum value
        "timestamp": datetime.now().isoformat()
    }
    
    tasks = await load_tasks()
    tasks.append(task)
    await save_tasks(tasks)
    return task_id


async def get_tasks() -> List[Dict[str, Any]]:
    """
    Retrieves all tasks from the task file.

    Returns:
        List[Dict[str, Any]]: A list of tasks.
    """
    tasks = await load_tasks()
    logging.debug(f"Retrieved {len(tasks)} tasks from {task_file}")
    return tasks


async def update_task_status(task_id: str, status: TaskStatus) -> None:
    """
    Updates the status of a task.

    Args:
        task_id (str): The ID of the task to update.
        status (TaskStatus): The new status for the task.
    """
    tasks = await load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status.value  # Use enum value
    await save_tasks(tasks)
    logging.info(f"Updated task {task_id} to status: {status}")


async def clear_tasks() -> None:
    """
    Clears all tasks from the task queue.
    """
    await save_tasks([])  # Save an empty JSON array
    logging.info(f"Tasks cleared from {task_file}")


async def remove_task(task_id: str) -> None:
    """
    Removes a specific task from the task queue.

    Args:
        task_to_remove (Dict[str, Any]): The task dictionary to remove.
    """
    tasks = await load_tasks()
    tasks = [task for task in tasks if task != task_id]
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


async def save_tasks(tasks: List[Dict]) -> None:
    """Save tasks to the task file."""
    async with aiofiles.open(task_file, 'w') as file:
        await file.write(json.dumps(tasks, indent=2))


# Get logger - don't configure here to avoid overriding main config
logger = logging.getLogger(__name__)
