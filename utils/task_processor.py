import asyncio
import logging
from threading import Thread, Event
from utils.task_file_handler import get_tasks, clear_tasks
from utils.synthesize import synthesize_text_to_speech as synthesize_edge_tts
from utils.synthesize_styletts2 import say_with_styletts2
from utils.env import setup_env

output_dir, urls_file, img_pth = setup_env()

def process_tasks(stop_event):
    while not stop_event.is_set():
        tasks = get_tasks()
        if tasks:  # Only print if the task list is not empty
            print(f"Tasks retrieved: {tasks}")  # Debug statement
        for task in tasks:
            if len(task) != 3:
                logging.error(f"Invalid task format: {task}")
                continue
            task_type, content, tts_engine = task
            if task_type == 'url':
                base_file_name = content.replace('http://', '').replace('https://', '').replace('/', '_')
                if tts_engine == "styletts2":
                    say_with_styletts2(content, base_file_name, output_dir)
                else:
                    asyncio.run(synthesize_edge_tts(content, output_dir, img_pth))
            elif task_type == 'text':
                base_file_name = content[:10].replace(' ', '_')
                if tts_engine == "styletts2":
                    say_with_styletts2(content, base_file_name, output_dir)
                else:
                    asyncio.run(synthesize_edge_tts(content, output_dir, img_pth))
        if tasks:  # Only clear tasks if there were any to process
            clear_tasks()
        stop_event.wait(5)  # Check for tasks every 5 seconds

def start_task_processor(stop_event):
    thread = Thread(target=process_tasks, args=(stop_event,))
    thread.daemon = True
    thread.start()
    return thread