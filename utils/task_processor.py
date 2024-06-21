import asyncio
import logging
from threading import Thread, Event
from utils.task_file_handler import get_tasks, clear_tasks
from utils.synthesize import synthesize_text_to_speech as synthesize_edge_tts
from utils.env import setup_env

output_dir, task_file, img_pth, sources_file, keywords_file = setup_env()

def process_tasks(stop_event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def process():
        while not stop_event.is_set():
            tasks = await get_tasks()
            if tasks:  # Only print if the task list is not empty
                print(f"Tasks retrieved: {tasks}")  # Debug statement
            for task in tasks:
                if len(task) != 3:
                    logging.error(f"Invalid task format: {task}")
                    continue
                task_type, content, tts_engine = task
                if task_type == "url":
                    if tts_engine == "styletts2":
                        from utils.synthesize_styletts2 import say_with_styletts2

                        await say_with_styletts2(content, output_dir, img_pth)
                    else:
                        await synthesize_edge_tts(content, output_dir, img_pth)
                elif task_type == "text":
                    if tts_engine == "styletts2":
                        from utils.synthesize_styletts2 import say_with_styletts2

                        await say_with_styletts2(content, output_dir, img_pth)
                    else:
                        await synthesize_edge_tts(content, output_dir, img_pth)
            if tasks:  # Only clear tasks if there were any to process
                await clear_tasks()
            await asyncio.sleep(5)  # Check for tasks every 5 seconds

    loop.run_until_complete(process())

def start_task_processor(stop_event):
    thread = Thread(target=process_tasks, args=(stop_event,))
    thread.daemon = True
    thread.start()
    return thread
