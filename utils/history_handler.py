#####################
# history_handler.py
#####################

# This module handles the history of processed items
# to make sure the same item is not processed twice

import os
import aiofiles
import json
import logging

HISTORY_FILE = "history.json"

async def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    async with aiofiles.open(HISTORY_FILE, "r") as file:
        content = await file.read()
        return json.loads(content) if content else []

async def save_history(history):
    async with aiofiles.open(HISTORY_FILE, "w") as file:
        await file.write(json.dumps(history, indent=2))

async def add_to_history(url):
    history = await load_history()
    if url not in history:
        history.append(url)
        await save_history(history)
        logging.info(f"URL added to history: {url}")

async def check_history(url):
    history = await load_history()
    return url in history