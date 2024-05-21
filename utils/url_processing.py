import os
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from threading import Event
from .synthesize import synthesize_text_to_speech

def process_urls(urls_file, stop_event: Event, output_dir, img_pth):
    processed_urls = set()

    def process():
        if os.path.exists(urls_file):
            with open(urls_file, 'r') as f:
                urls = f.readlines()

            updated_urls = []
            for url in urls:
                url = url.strip()
                if url and url not in processed_urls:
                    try:
                        asyncio.run(synthesize_text_to_speech(url, output_dir, img_pth))
                        processed_urls.add(url)
                        logging.info(f"Processed: {url}")
                    except Exception as e:
                        logging.error(f"Error processing URL {url}: {e}")
                        updated_urls.append(url)
                else:
                    updated_urls.append(url)

            with open(urls_file, 'w') as f:
                for url in updated_urls:
                    f.write(url + '\n')

    class URLFileHandler(PatternMatchingEventHandler):
        def __init__(self, process_function, patterns):
            super().__init__(patterns=patterns)
            self.process_function = process_function

        def on_modified(self, event):
            if event.src_path.endswith("urls.txt"):
                self.process_function()

    event_handler = URLFileHandler(process, patterns=["*urls.txt"])
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    finally:
        observer.stop()
        observer.join()

def add_url_to_file(url, urls_file):
    with open(urls_file, 'a') as f:
        f.write(f"{url}\n")
