import os
import datetime
import random
import asyncio
import logging
import time
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import edge_tts
from edge_tts import VoicesManager
from typing import List
from threading import Thread, Event
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TRCK, APIC
from PIL import Image, ImageDraw, ImageFont
import trafilatura
import requests
from bs4 import BeautifulSoup
from io import BytesIO, StringIO
import tldextract
import re
from contextlib import asynccontextmanager
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

app = FastAPI()

# Background thread stop event
stop_event = Event()

# Set up logging to the proecess_log.txt file in the root directory of the project
log_file_path = "process_log.txt"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', 
                    handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()])

# Event to signal the thread to exit
stop_event = Event()


# You can set up where to store the output files by creating a .env file in the root directory
# This checks, if the.env file exists in the root directory of the project and loads it
def check_env_file_exists(directory='.'):
    env_file_path = os.path.join(directory, '.env')
    return os.path.isfile(env_file_path)

if check_env_file_exists():
    from dotenv import load_dotenv
    load_dotenv()
    output_dir = os.getenv("OUTPUT_DIR")
    urls_file = os.getenv("URL_FILE")
    img_pth = os.getenv("IMG_PATH")

# if the.env file does not exist, set the default values for the output directory and the urls file path
else:
    output_dir = "Output"
    urls_file = "urls.txt"
    img_pth = "front.jpg"

class URLRequest(BaseModel):
    url: str


# To organize the output files, we create a folder with the current date in the format YYYYMMDD and store all the output files there.
# This way you get a new folder each day

def get_date_subfolder():
    current_date = datetime.date.today().strftime("%Y%m%d")
    subfolder = os.path.join(output_dir, current_date)
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
    return subfolder

async def get_output_files():
    subfolder = get_date_subfolder()
    file_number = 1

# Currently, the output files are just named with a 3 digit number, starting at 001 (if no file exists yet).
# If there are already files in the output folder, it will start at the highest number +1.

    while True:
        base_file_name = f"{subfolder}/{file_number:03d}"
        mp3_file_name = f"{base_file_name}.mp3"
        md_file_name = f"{base_file_name}.md"
        if not os.path.exists(mp3_file_name) and not os.path.exists(md_file_name):
            return base_file_name, mp3_file_name, md_file_name
        else:
            file_number += 1

def create_image_with_date(image_path: str, output_path: str, date_text: str):
    if not os.path.exists(output_path):
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        font_path = "Fonts/PermanentMarker.ttf"
        font = ImageFont.truetype(font_path, 50)
        width, height = image.size
        text_bbox = draw.textbbox((0, 0), date_text, font=font)
        text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        position = ((width - text_width) // 2, height - text_height - 35)
        draw.text(position, date_text, font=font, fill="black")
        image.save(output_path)

def add_mp3_tags(mp3_file: str, title: str):
    track_number = os.path.basename(mp3_file).split('_')[-1].split('.')[0]
    try:
        audio = ID3(mp3_file)
    except Exception:
        audio = ID3()
    audio.add(TIT2(encoding=3, text=title))
    audio.add(TALB(encoding=3, text=f"READ2ME{datetime.date.today().strftime('%Y%m%d')}"))
    audio.add(TPE1(encoding=3, text="READ2ME"))
    audio.add(TCON(encoding=3, text="Spoken Audio"))
    audio.add(TRCK(encoding=3, text=str(track_number)))
    date_text = datetime.date.today().strftime("%Y-%m-%d")
    image_path = img_pth
    output_image_path = os.path.join(get_date_subfolder(), "cover.jpg")
    create_image_with_date(image_path, output_image_path, date_text)
    with open(output_image_path, "rb") as img_file:
        audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img_file.read()))
    audio.save(mp3_file)

def is_pdf_or_html(url):
    try:
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get('Content-Type')
        if 'application/pdf' in content_type:
            return 'PDF'
        elif 'text/html' in content_type:
            return 'HTML'
        else:
            return 'Other'
    except requests.exceptions.RequestException:
        return None

def extract_text(url_or_html, is_html=True):
    if is_html:
        downloaded = trafilatura.fetch_url(url_or_html)
        if downloaded is None:
            return None, None

        domainname = tldextract.extract(url_or_html)
        main_domain = f"{domainname.domain}.{domainname.suffix}"
        result = trafilatura.extract(downloaded, include_comments=False)
        soup = BeautifulSoup(downloaded, 'html.parser')
    else:
        result = url_or_html
        soup = BeautifulSoup(url_or_html, 'html.parser')
        main_domain = "unknown"
        
    title = soup.find('title').text if soup.find('title') else ''
    date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
    timestamp = date_tag['content'] if date_tag else ''
    article_content = f"{title}.\n\n" if title else ""
    article_content += f"From {main_domain}.\n\n"
    authors = []
    for attr in ['name', 'property']:
        author_tags = soup.find_all('meta', attrs={attr: 'author'})
        for tag in author_tags:
            if tag and tag.get('content'):
                authors.append(tag['content'])
    authors = sorted(set(authors))
    if authors:
        article_content += "Written by: " + ", ".join(authors) + ".\n\n"
    date_formats = ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S"]
    date_str = ''
    if timestamp:
        for date_format in date_formats:
            try:
                date = datetime.datetime.strptime(timestamp, date_format)
                date_str = date.strftime("%B %d, %Y")
                break
            except ValueError:
                continue
    if date_str:
        article_content += f"Published on: {date_str}.\n\n"
    if result:
        lines = result.split('\n')
        filtered_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if len(line.split()) < 15:
                if i + 1 < len(lines) and len(lines[i + 1].split()) < 15:
                    while i < len(lines) and len(lines[i].split()) < 15:
                        i += 1
                    continue
            filtered_lines.append(line)
            i += 1
        formatted_text = '\n\n'.join(filtered_lines)
        formatted_text is re.sub(r'\n[\-_]\n', '\n\n', formatted_text)
        formatted_text is re.sub(r'[\-_]{3,}', '', formatted_text)
        article_content += formatted_text
    return article_content, title

async def synthesize_text_to_speech(url: str):
    content_type = is_pdf_or_html(url)
    if content_type == 'HTML':
        try:
            result = extract_text(url)
            if result is None or len(result) != 2:
                raise ValueError("Extracted result does not contain exactly two elements")
            text, title = result
        except Exception as e:
            logging.error(f"Failed to extract text and title from URL {url}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract text and title from URL: {e}")
    else:
        logging.error(f"Unsupported content type or unable to determine content type for URL {url}")
        raise HTTPException(status_code=400, detail="Unsupported content type or unable to determine content type.")

    if not text:
        logging.error(f"No text extracted from the provided URL {url}")
        raise HTTPException(status_code=400, detail="No text extracted from the provided URL")

    base_file_name, mp3_file, md_file = await get_output_files()

    with open(md_file, 'w') as md_file_handle:
        md_file_handle.write(text)
        md_file_handle.write(f"\n\nSource: {url}")

    voices = await VoicesManager.create()
    multilingual_voices = [voice for voice in voices.voices if "MultilingualNeural" in voice["Name"]]
    if not multilingual_voices:
        logging.error("No MultilingualNeural voices found")
        raise HTTPException(status_code=500, detail="No MultilingualNeural voices found")

    voice = random.choice(multilingual_voices)["Name"]

    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(mp3_file)

    add_mp3_tags(mp3_file, title)

    logging.info(f"Successfully processed URL {url}")
    return mp3_file, md_file

def process_urls():
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
                        asyncio.run(synthesize_text_to_speech(url))
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


    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    finally:
        observer.stop()
        observer.join()

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = Thread(target=process_urls)
    thread.daemon = True
    thread.start()
    try:
        yield
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()
        thread.join()
        print("Clean shutdown completed.")

app = FastAPI(lifespan=lifespan)

processed_keys = set()

@app.post("/synthesize/")
async def synthesize(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    with open(urls_file, 'a') as f:
        f.write(f"{request.url}\n")
    return {"message": "URL added to the processing list"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
