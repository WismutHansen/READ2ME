#!/usr/bin/env python3
# main.py
# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import re
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from logging.handlers import TimedRotatingFileHandler
from threading import Event
from typing import List, Optional, Union, Literal, Dict, Any
from urllib.parse import urlparse
import json

# Suppress pkg_resources deprecation warning from perth library
warnings.filterwarnings(
    "ignore", message="pkg_resources is deprecated", category=UserWarning
)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel
from tzlocal import get_localzone
from TTS.tts_engines import EdgeTTSEngine, OpenAITTSEngine, KokoroTTSEngine
from database.crud import (
    fetch_available_media,
    get_article,
    get_text,
    get_podcast,
    delete_audio,
)
from database.models import create_or_update_tables
from database.crud import get_voice_settings, update_voice_settings
from utils.env import setup_env
from utils.history_handler import add_to_history
from utils.source_manager import read_sources, update_sources
from utils.task_file_handler import (
    add_task,
    get_task_count,
    get_tasks,
    remove_task,
)
from utils.task_processor import start_task_processor
from utils.rssfeed import get_articles_from_feed, load_feeds_from_json
from utils.common_enums import InputType, TaskType
from llm.Local_Ollama import LOW_VRAM  # Added for LOW_VRAM status logging


# Load environment variables
output_dir, task_file, img_pth, sources_file = setup_env()

load_dotenv()
FRONTEND_IP = os.environ.get("FRONTEND_IP")

# Background thread stop event
stop_event = Event()

# Task to manage article fetching
fetch_task = None  # Initialized as None, will hold the asyncio Task


def check_output_dir():
    """
    Checks if the OUTPUT_FOLDER specified in .env exists.
    Creates it if not.

    Returns:
        str: The path to the OUTPUT_FOLDER.
    """

    output_folder = os.getenv("OUTPUT_FOLDER")

    if not output_folder:
        raise ValueError("OUTPUT_FOLDER is not set in the environment variables.")

    # Check if the output folder exists
    if not os.path.exists(output_folder):
        logger = logging.getLogger()
        logger.info(f"Output folder '{output_folder}' does not exist. Creating it...")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Failed to create OUTPUT_FOLDER: {e}")

    return output_folder


def setup_logging(log_file_path):
    logger = logging.getLogger()

    # Prevent duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = TimedRotatingFileHandler(
        log_file_path, when="midnight", interval=1, backupCount=14
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# Set up logging - only once per process
log_file_path = os.path.abspath("process_log.txt")
logger = None
_logging_initialized = False


def initialize_logging():
    global logger, _logging_initialized
    if not _logging_initialized:
        try:
            logger = setup_logging(log_file_path)
            # Only show banner in main server process (not reload worker)
            if os.getenv("RUN_MAIN") != "true":
                logger.info(f"Logging setup completed. Log file path: {log_file_path}")
                _logging_initialized = True
        except Exception as e:
            # Fallback to print if logging setup fails
            print(f"Error setting up logging: {e}")
    return logger


# Initialize logging
initialize_logging()
if logger:  # Check if logger was successfully initialized
    logger.info(f"Running in Low VRAM mode: {LOW_VRAM}")


class URLRequest(BaseModel):
    url: str
    tts_engine: str = "edge"  # Default to edge-tts
    task: TaskType = TaskType.FULL  # Default to full processing


class TextRequest(BaseModel):
    text: str
    tts_engine: str = "edge"  # Default to edge-tts
    task: TaskType = TaskType.FULL  # Default to full processing


class Source(BaseModel):
    url: str
    keywords: List[str]
    category: str = "General"


class SourceUpdate(BaseModel):
    global_keywords: Optional[List[str]] = None
    sources: Optional[List[Source]] = None


class TaskRemoveRequest(BaseModel):
    task_id: str
    type: str
    content: str
    tts_engine: str
    task: Union[str, dict, None] = None


class BatchArticlesRequest(BaseModel):
    urls: List[str]
    mode: Literal["full", "summary", "podcast"]
    tts_engine: str = "edge"


class RemoveAudioItem(BaseModel):
    content_type: Literal["article", "text", "podcast"]
    id: str


class RemoveAudioRequest(BaseModel):
    items: List[RemoveAudioItem]


class IntervalRequest(BaseModel):
    interval: Optional[int] = None  # Interval in minutes, None for default schedule


class VoiceSettingUpdate(BaseModel):
    voice_id: str
    is_active: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fetch_task, stop_event
    stop_event.clear()  # Ensure the event is clear before starting the thread
    thread = start_task_processor(stop_event)
    fetch_task = asyncio.create_task(schedule_fetch_articles())  # Initialize fetch_task
    articles_cache_task = asyncio.create_task(start_articles_cache_refresh())
    try:
        yield
    except Exception as e:
        logging.error(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish
        fetch_task.cancel()  # Cancel the fetch task
        articles_cache_task.cancel()  # Cancel the articles cache refresh task
        try:
            await fetch_task  # Wait for the fetch task to finish
            await (
                articles_cache_task
            )  # Wait for the articles cache refresh task to finish
        except asyncio.CancelledError:
            logging.info("Fetch task cancelled.")
            logging.info("Articles cache refresh task cancelled.")
        logging.info("Clean shutdown completed.")


app = FastAPI(
    lifespan=lifespan,
    title="Read2Me API",
    description="API for text-to-speech conversion and more",
    version="0.1.7",
)

mcp = FastApiMCP(app)

# Mount the MCP server directly to your FastAPI app
mcp.mount()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(FRONTEND_IP),
        "http://localhost:3001",
        "http://localhost:3000",
        "http://192.168.1.*",  # HTTP for all IPs in 192.168.1.x range
        "https://192.168.1.*",  # HTTPS for all IPs in 192.168.1.x range
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Get the output directory from environment variable
output_dir = os.getenv("OUTPUT_DIR", "Output")

# Mount the output directory using the absolute path from environment
app.mount("/Output", StaticFiles(directory=output_dir), name="static")


# Helper function to convert absolute paths to relative paths for the frontend
def get_relative_path(absolute_path: str) -> str:
    try:
        # Remove any "Output/" prefix from the path
        if absolute_path.startswith(output_dir + os.path.sep):
            return absolute_path[len(output_dir + os.path.sep) :]
        return absolute_path
    except ValueError:
        # If the paths are on different drives or invalid
        return absolute_path


# Helper function to convert relative paths to absolute paths for the backend
def get_absolute_path(relative_path: str) -> str:
    if os.path.isabs(relative_path):
        return relative_path
    # Remove any "Output/" prefix if it exists
    if relative_path.startswith(output_dir + os.path.sep):
        relative_path = relative_path[len(output_dir + os.path.sep) :]
    return os.path.join(output_dir, relative_path)


@app.get("/v1/queue/status")
async def get_queue_status():
    task_count = await get_task_count()  # get number of tasks in queue
    tasks = await get_tasks()  # retrieve list of tasks

    return {"task_count": task_count, "tasks": tasks}


@app.delete("/v1/queue/remove")
async def remove_task_endpoint(task: TaskRemoveRequest):
    task_id = task.task_id
    existing_tasks = await get_tasks()  # This is presumably a list of dicts

    # Example check: if your tasks are stored like [{"id": "123", ...}, {"id": "abc", ...}]
    # then we see if `task_id` matches any t["id"] in the list
    if not any(t.get("id") == task_id for t in existing_tasks):
        raise HTTPException(status_code=404, detail="Task not found in queue")

    await remove_task(task_id)
    return {"status": "success", "message": "Task removed from queue"}


@app.post("/v1/url/full")
async def url_audio_full(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    logging.info(
        f"URL type: {type(request.url)}, TTS Engine type: {type(request.tts_engine)}"
    )

    # Validate URL
    parsed_url = urlparse(request.url)
    if not all([parsed_url.scheme, parsed_url.netloc]) or parsed_url.scheme not in [
        "http",
        "https",
    ]:
        logging.error(f"Invalid URL received: {request.url}")
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )

    await add_task(InputType.URL, request.url, request.tts_engine, TaskType.FULL)
    return {"message": "URL added to the READ2ME task list"}


@app.post("/v1/url/podcast")
async def url_podcast(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    logging.info(
        f"URL type: {type(request.url)}, TTS Engine type: {type(request.tts_engine)}"
    )

    # Validate URL
    parsed_url = urlparse(request.url)
    if not all([parsed_url.scheme, parsed_url.netloc]) or parsed_url.scheme not in [
        "http",
        "https",
    ]:
        logging.error(f"Invalid URL received: {request.url}")
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )
    await add_task("url", request.url, request.tts_engine, "podcast")
    return {"message": "URL added to the READ2ME task list"}


@app.post("/v1/url/story")
async def url_story(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    logging.info(
        f"URL type: {type(request.url)}, TTS Engine type: {type(request.tts_engine)}"
    )

    # Validate URL
    parsed_url = urlparse(request.url)
    if not all([parsed_url.scheme, parsed_url.netloc]) or parsed_url.scheme not in [
        "http",
        "https",
    ]:
        logging.error(f"Invalid URL received: {request.url}")
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )
    await add_task(InputType.URL, request.url, request.tts_engine, TaskType.STORY)
    return {"message": "URL added to the READ2ME task list"}


@app.post("/v1/url/summary")
async def url_audio_summary(request: URLRequest):
    logging.info(f"Received URL/summary: {request.url}")
    logging.info(
        f"URL type: {type(request.url)}, TTS Engine type: {type(request.tts_engine)}, task: summary"
    )

    # Validate URL
    parsed_url = urlparse(request.url)
    if not all([parsed_url.scheme, parsed_url.netloc]) or parsed_url.scheme not in [
        "http",
        "https",
    ]:
        logging.error(f"Invalid URL received: {request.url}")
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )
    await add_task(InputType.URL, request.url, request.tts_engine, TaskType.TLDR)
    return {"message": "URL/Summary added to the READ2ME task list"}


@app.post("/v1/text/full")
async def read_text(request: TextRequest):
    logging.info(f"Received text: {request.text}")
    await add_task(InputType.TEXT, request.text, request.tts_engine, TaskType.FULL)
    return {"message": "Text added to the READ2ME task list"}


@app.post("/v1/text/summary")
async def read_text_summary(request: TextRequest):
    logging.info("Received task text/summary}")
    logging.info(
        f"URL type: {type(request.text)}, TTS Engine type: {type(request.tts_engine)}, task: summary"
    )

    await add_task(InputType.TEXT, request.text, request.tts_engine, TaskType.TLDR)
    return {"message": "text/summary added to the READ2ME task list"}


@app.post("/v1/text/podcast")
async def read_text_podcast(request: TextRequest):
    logging.info("Received task text/podcast}")
    logging.info(
        f"URL type: {type(request.text)}, TTS Engine type: {type(request.tts_engine)}, task: podcast"
    )

    await add_task(InputType.TEXT, request.text, request.tts_engine, TaskType.PODCAST)
    return {"message": "text/podcast added to the READ2ME task list"}


@app.post("/v1/pdf/full")
async def read_pdf_summary(request: TextRequest):
    return {"message": "Endpoint not yet implemented"}


@app.post("/v1/sources/fetch")
async def fetch_sources(request: Request):
    from utils.sources import fetch_articles

    await fetch_articles()
    logging.info(f"Received manual article fetch request")
    return {"message": "Checking for new articles in sources"}


@app.post("/v1/sources/add")
async def api_update_sources(update: SourceUpdate):
    """Update sources and optionally refresh the articles cache if new RSS feeds were added."""
    # Update the sources and get back if we need to refresh
    data, needs_refresh = update_sources(
        global_keywords=update.global_keywords,
        sources=update.sources,
    )

    # If we added new RSS feeds, refresh the cache
    if needs_refresh:
        try:
            await refresh_articles_cache()
        except Exception as e:
            logging.error(f"Error refreshing articles cache: {e}")

    return data


@app.get("/v1/sources/get")
async def api_get_sources():
    return read_sources()


# New endpoint to force re-process a URL in case of e.g. a change in the source
@app.post("/v1/url/reprocess")
async def url_audio_reprocess(request: URLRequest):
    logging.info(f"Reprocessing URL: {request.url}")
    await add_to_history(request.url)  # Add to history to avoid future re-processing
    await add_task(InputType.URL, request.url, request.tts_engine, request.task)
    return {"message": "URL reprocessing added to the READ2ME task list"}


@app.get("/v1/audio-files")
async def get_audio_files(request: Request, page: int = 1, limit: int = 20):
    audio_files = []
    total_files = 0

    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith(".mp3"):
                total_files += 1
                if (page - 1) * limit <= len(audio_files) < page * limit:
                    relative_path = get_relative_path(os.path.join(root, file))
                    audio_url = f"/v1/audio/{relative_path}"
                    audio_files.append(
                        {
                            "audio_file": audio_url,
                            "title": os.path.splitext(file)[0].replace("_", " "),
                        }
                    )

                if len(audio_files) >= limit:
                    break

        if len(audio_files) >= limit:
            break

    return JSONResponse(
        content={
            "audio_files": audio_files,
            "total_files": total_files,
            "page": page,
            "limit": limit,
            "total_pages": (total_files + limit - 1) // limit,
        }
    )


@app.get("/v1/audio/{file_path:path}")
async def get_audio(file_path: str):
    full_path = get_absolute_path(file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(full_path, media_type="audio/mpeg")


@app.get("/v1/audio-file/{file_path:path}")
async def get_audio_file_text(file_path: str, type: str = None):
    logging.info(f"Received request for file_path: {file_path}, type: {type}")

    # Normalize the file path to use the correct directory separator
    file_path = os.path.normpath(file_path)
    logging.info(f"Normalized path: {file_path}")

    # Remove any extensions from the file path
    base_path = os.path.splitext(file_path)[0]
    logging.info(f"Base path: {base_path}")

    if type == "audio":
        # Return the audio file
        audio_file_path = get_absolute_path(f"{base_path}.mp3")
        logging.info(f"Audio file path: {audio_file_path}")
        if not os.path.isfile(audio_file_path):
            logging.error(f"Audio file not found at: {audio_file_path}")
            raise HTTPException(status_code=404, detail="Audio file not found")
        return FileResponse(audio_file_path, media_type="audio/mpeg")

    # Default to returning text content
    text_file_path = get_absolute_path(f"{base_path}.md")
    logging.info(f"Text file path: {text_file_path}")

    if not os.path.isfile(text_file_path):
        logging.error(f"Text file not found at: {text_file_path}")
        raise HTTPException(
            status_code=404, detail=f"Text file not found: {text_file_path}"
        )

    try:
        with open(text_file_path, "r", encoding="utf-8") as file:
            text = file.read()

        relative_audio_path = get_relative_path(f"{base_path}.mp3")
        logging.info(f"Returning relative audio path: {relative_audio_path}")

        return JSONResponse(
            content={
                "text": text,
                "title": os.path.basename(base_path).replace("_", " "),
                "audio_file": relative_audio_path,
            }
        )
    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# Endpoint for fetching the VTT file
@app.get("/v1/vtt-file/{file_path:path}")
async def get_vtt_file(file_path: str):
    # Normalize the file path to use the correct directory separator
    file_path = os.path.normpath(file_path)

    # Construct the full path to the VTT file
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    vtt_file_path = get_absolute_path(f"{file_path}.vtt")

    if not os.path.isfile(vtt_file_path):
        raise HTTPException(
            status_code=404, detail=f"VTT file not found: {vtt_file_path}"
        )

    return FileResponse(vtt_file_path, media_type="text/vtt")


clients = []


@app.websocket("/ws/playback")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process the playback position data here
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        clients.remove(websocket)


def generate_article_id(date_folder, mp3_filename):
    # Extract the first three digits from the MP3 filename
    digits = re.findall(r"\d+", mp3_filename)
    if digits:
        return f"{date_folder}_{digits[0][:3]}"
    return f"{date_folder}_000"  # Fallback if no digits found


@app.get("/v1/article/{article_id}")
async def get_article_from_db(article_id: str):
    try:
        article = get_article(article_id)
        if not article:
            # Log the article ID that wasn't found
            logging.error(f"Article not found in database: {article_id}")
            raise HTTPException(status_code=404, detail="Article not found")

        # Format the audio file path
        audio_file = article.get("audio_file")
        if audio_file:
            audio_file = audio_file.lstrip("/")
            audio_file = (
                audio_file
                if audio_file.startswith("Output/")
                else f"Output/{audio_file}"
            )

        # Log the article data being returned
        logging.info(f"Returning article data: {article}")

        content = {
            "id": article_id,
            "title": article.get("title"),
            "date": article.get("date_published") or article.get("date_added"),
            "audio_file": audio_file,
            "content": article.get("plain_text"),
            "tl_dr": article.get("tl_dr"),
        }
        return JSONResponse(content=content)
    except Exception as e:
        logging.error(f"Error fetching article {article_id}: {str(e)}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to fetch article", "error": str(e)},
        )


@app.get("/v1/podcast/{podcast_id}")
async def get_podcast_from_db(podcast_id: str):
    try:
        podcast = get_podcast(podcast_id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        # Format the audio file path
        audio_file = podcast.get("audio_file")
        if audio_file:
            audio_file = audio_file.lstrip("/")
            audio_file = (
                audio_file
                if audio_file.startswith("Output/")
                else f"Output/{audio_file}"
            )

        content = {
            "id": podcast_id,
            "title": podcast.get("title"),
            "date": podcast.get("date_added"),
            "audio_file": audio_file,
            "content": podcast.get("text"),
        }
        return JSONResponse(content=content)
    except Exception as e:
        logging.error(f"Error fetching podcast {podcast_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to fetch podcast", "error": str(e)},
        )


@app.get("/v1/text/{text_id}")
async def get_text_from_db(text_id: str):
    try:
        text = get_text(text_id)
        if not text:
            raise HTTPException(status_code=404, detail="Text not found")

        # Format the audio file path
        audio_file = text.get("audio_file")
        if audio_file:
            audio_file = audio_file.lstrip("/")
            audio_file = (
                audio_file
                if audio_file.startswith("Output/")
                else f"Output/{audio_file}"
            )

        content = {
            "id": text_id,
            "title": text.get("title"),
            "date": text.get("date_added"),
            "audio_file": audio_file,
            "content": text.get("text"),
            "tl_dr": text.get("tl_dr"),
        }
        return JSONResponse(content=content)
    except Exception as e:
        logging.error(f"Error fetching text {text_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to fetch text", "error": str(e)},
        )


@app.get("/v1/available-media")
async def get_available_media():
    try:
        media = fetch_available_media()
        return media
    except Exception as e:
        logging.error(f"Error in get_available_media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/schedule/set-interval")
async def set_fetch_interval(request: IntervalRequest):
    """
    Set the interval for fetching articles. If interval is None, use the predefined times.
    """
    global fetch_task, stop_event

    # Update the interval
    interval = request.interval

    # Cancel the existing fetch task if running
    if fetch_task:
        stop_event.set()
        fetch_task.cancel()
        try:
            await fetch_task
        except asyncio.CancelledError:
            logging.info("Existing fetch task cancelled.")

    # Clear the stop event and restart the task with the new interval
    stop_event.clear()
    fetch_task = asyncio.create_task(schedule_fetch_articles(interval=interval))

    message = (
        f"Fetch interval set to {interval} minutes."
        if interval is not None
        else "Fetch interval set to default schedule."
    )
    logging.info(message)
    return {"message": message}


async def schedule_fetch_articles(interval: Optional[int] = None):
    from utils.sources import fetch_articles

    async def job():
        logging.info("Fetching articles...")
        await fetch_articles()

    local_tz = get_localzone()
    logging.info(f"Using local timezone: {local_tz}")

    while not stop_event.is_set():
        now = datetime.now(local_tz)
        if interval is not None:
            # Calculate the next run based on the interval
            next_run = now + timedelta(minutes=interval)
            next_run = next_run.replace(second=0, microsecond=0)
        else:
            # Use predefined target times
            target_times = [
                time(0, 0),
                time(5, 0),
                time(12, 0),
                time(19, 0),
            ]  # Midnight, 5:00 AM, 12:00 PM, 7:00 PM

            for target_time in target_times:
                if now.time() <= target_time:
                    next_run = now.replace(
                        hour=target_time.hour,
                        minute=target_time.minute,
                        second=0,
                        microsecond=0,
                    )
                    break
            else:
                next_run = now.replace(
                    hour=target_times[0].hour,
                    minute=target_times[0].minute,
                    second=0,
                    microsecond=0,
                )
                next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        logging.info(
            f"Next scheduled run at {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
        logging.info(f"Waiting for {wait_seconds:.2f} seconds")

        try:
            await asyncio.sleep(wait_seconds)
            if not stop_event.is_set():
                await job()
        except asyncio.CancelledError:
            logging.info("Scheduled fetch task cancelled.")
            break


# Cache for today's articles
articles_cache = {"last_updated": None, "articles": []}


async def refresh_articles_cache():
    """Background task to refresh the articles cache."""
    global articles_cache

    feeds = load_feeds_from_json("my_feeds.json")
    all_todays_articles = []

    for feed in feeds:
        feed_url = feed["url"]
        category = feed["category"]
        todays_articles = get_articles_from_feed(feed_url, category)
        all_todays_articles.extend(todays_articles)

    articles_cache["articles"] = all_todays_articles
    articles_cache["last_updated"] = datetime.now()
    logging.info(f"Articles cache refreshed at {articles_cache['last_updated']}")


async def start_articles_cache_refresh():
    """Start the background task to refresh articles cache every 5 minutes."""
    while True:
        try:
            await refresh_articles_cache()
            await asyncio.sleep(300)  # Sleep for 5 minutes
        except Exception as e:
            logging.error(f"Error refreshing articles cache: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying if there's an error


@app.get("/v1/feeds/get")
async def get_feeds():
    """API endpoint to return the contents of my_feeds.json."""
    feeds = load_feeds_from_json("my_feeds.json")
    if feeds:
        return JSONResponse(content={"feeds": feeds})
    else:
        raise HTTPException(
            status_code=404, detail="Feeds data is unavailable or invalid."
        )


@app.get("/v1/feeds/get_todays_articles")
async def get_todays_articles():
    """API endpoint to return today's articles from all feeds with categories."""
    global articles_cache

    if not articles_cache["articles"]:
        # Initial fetch if cache is empty
        await refresh_articles_cache()

    if articles_cache["articles"]:
        return JSONResponse(content={"articles": articles_cache["articles"]})
    else:
        return JSONResponse(
            content={"message": "No articles published today across all feeds."},
            status_code=204,
        )


@app.post("/v1/articles/batch")
async def process_articles_batch(request: BatchArticlesRequest):
    """
    Process multiple articles in batch mode.
    """
    try:
        results = []
        for url in request.urls:
            url_request = URLRequest(url=url, tts_engine=request.tts_engine)

            try:
                if request.mode == "full":
                    await url_audio_full(url_request)
                elif request.mode == "summary":
                    await url_audio_summary(url_request)
                elif request.mode == "podcast":
                    await url_podcast(url_request)

                results.append({"url": url, "status": "success"})
            except Exception as e:
                results.append({"url": url, "status": "error", "error": str(e)})
                logging.error(f"Error processing URL {url}: {str(e)}")

        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count

        return {
            "message": f"Processed {len(results)} articles: {success_count} successful, {error_count} failed",
            "results": results,
        }
    except Exception as e:
        logging.error(f"Batch processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/audio")
async def remove_audio_files(request: RemoveAudioRequest):
    removed_items = []
    errors = []

    for item in request.items:
        try:
            # Get the item from the appropriate table
            if item.content_type == "article":
                db_item = get_article(item.id)
            elif item.content_type == "text":
                db_item = get_text(item.id)
            else:  # podcast
                db_item = get_podcast(item.id)

            if not db_item or "audio_file" not in db_item or not db_item["audio_file"]:
                errors.append(
                    {
                        "id": item.id,
                        "error": f"{item.content_type} not found or has no audio file",
                    }
                )
                continue

            audio_file_path = db_item["audio_file"]

            # Get absolute path for file operations
            abs_audio_file_path = os.path.abspath(audio_file_path)

            logging.info(f"Attempting to delete audio file: {abs_audio_file_path}")
            # Remove the audio file if it exists
            if os.path.exists(abs_audio_file_path):
                logging.info(f"Found audio file, deleting: {abs_audio_file_path}")
                os.remove(abs_audio_file_path)

                # Also remove the VTT file if it exists for articles
                if item.content_type == "article":
                    vtt_file_path = abs_audio_file_path.replace(".mp3", ".vtt")
                    if os.path.exists(vtt_file_path):
                        logging.info(f"Found VTT file, deleting: {vtt_file_path}")
                        os.remove(vtt_file_path)
            else:
                logging.warning(f"Audio file not found at path: {abs_audio_file_path}")

            # Update database to remove audio file reference
            if delete_audio(item.content_type, item.id):
                removed_items.append({"id": item.id, "content_type": item.content_type})
                logging.info(
                    f"Successfully processed deletion for {item.content_type} with id {item.id}"
                )
            else:
                errors.append(
                    {
                        "id": item.id,
                        "error": f"Failed to update {item.content_type} in database",
                    }
                )

        except Exception as e:
            logging.error(
                f"Error deleting {item.content_type} with id {item.id}: {str(e)}"
            )
            errors.append({"id": item.id, "error": str(e)})

    return {"removed": removed_items, "errors": errors}


@app.get("/v1/status")
async def get_status() -> Dict[str, Any]:
    """
    Retrieve the current system status, including the task queue and recent errors.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - "queue": Task counts categorized by status.
            - "errors": A list of the last 10 logged errors.
            - "lastUpdate": The current timestamp.

    Raises:
        HTTPException: If an error occurs while processing the request.
    """
    try:
        # Load task queue statistics
        tasks: List[Dict[str, Any]] = []
        if os.path.isfile(task_file) and os.path.getsize(task_file) > 0:
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    raw_tasks = json.load(f)
                    tasks = [
                        t for t in raw_tasks if isinstance(t, dict)
                    ]  # Only keep dictionaries
            except json.JSONDecodeError:
                logging.error(
                    f"Invalid JSON format in {task_file}. Resetting tasks list."
                )
                tasks = []  # Default to an empty list

        # Load recent errors from the log file
        errors: List[Dict[str, str]] = []
        log_file: str = "process_log.txt"
        if os.path.isfile(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f.readlines()[-50:]:  # Read last 50 lines
                        if "ERROR" in line:
                            parts = line.split("ERROR")
                            if len(parts) > 1:
                                timestamp: str = parts[0].strip().split()[0]
                                error_detail: str = parts[1].strip()
                                error_type: str = error_detail.split(":")[0].strip()
                                message: str = error_detail.split(":", 1)[1].strip()
                                errors.append(
                                    {
                                        "timestamp": timestamp,
                                        "type": error_type,
                                        "message": message,
                                    }
                                )
            except FileNotFoundError:
                pass  # No log file found, ignore errors list

        return {
            "queue": {
                "pending": sum(
                    1
                    for t in tasks
                    if isinstance(t, dict) and t.get("status") == "pending"
                ),
                "processing": sum(
                    1
                    for t in tasks
                    if isinstance(t, dict) and t.get("status") == "processing"
                ),
                "completed": sum(
                    1
                    for t in tasks
                    if isinstance(t, dict) and t.get("status") == "completed"
                ),
                "failed": sum(
                    1
                    for t in tasks
                    if isinstance(t, dict) and t.get("status") == "failed"
                ),
            },
            "tasks": [
                {
                    "id": t.get("id"),
                    "status": t.get("status"),
                    "progress": t.get("progress", 0),
                    "tts_engine": t.get("tts_engine"),
                    "task": t.get("task"),
                }
                for t in tasks
                if isinstance(t, dict) and t.get("status") == "processing"
            ],
            "errors": errors[-10:],  # Return only the last 10 errors
            "lastUpdate": datetime.now().isoformat(),
        }
    except Exception as e:
        logging.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/voices/{engine_name}")
async def get_voices(engine_name: str) -> List[dict]:
    """
    Retrieve available voices for a given text-to-speech (TTS) engine.

    Args:
        engine_name (str): The name of the TTS engine (e.g., "kokoro", "openai", "edge").

    Returns:
        List[dict]: A list of available voices with their activation status.
    """
    # Get available voices from the specified engine
    if engine_name == "kokoro":
        engine = KokoroTTSEngine()
    elif engine_name == "openai":
        engine = OpenAITTSEngine()
    else:
        engine = EdgeTTSEngine()

    available_voices = await engine.get_available_voices()

    # Get stored settings
    stored_settings = {
        vs["voice_id"]: vs["is_active"] for vs in get_voice_settings(engine_name)
    }

    # Combine available voices with stored settings
    voice_settings = [
        {"voice_id": voice, "is_active": stored_settings.get(voice, True)}
        for voice in available_voices
    ]

    return voice_settings


@app.post("/v1/voices/{engine_name}")
async def update_voices(engine_name: str, voices: List[VoiceSettingUpdate]) -> dict:
    """
    Update the activation status of voices for a given text-to-speech (TTS) engine.

    Args:
        engine_name (str): The name of the TTS engine (e.g., "kokoro", "openai", "edge").
        voices (List[VoiceSettingUpdate]): A list of voice settings to update.

    Returns:
        dict: A success message confirming the update.
    """
    update_voice_settings(engine_name, [v.model_dump() for v in voices])
    return {"status": "success"}


if __name__ == "__main__":
    print("""

        ██████╗ ███████╗ █████╗ ██████╗ ██████╗ ███╗   ███╗███████╗
        ██╔══██╗██╔════╝██╔══██╗██╔══██╗╚════██╗████╗ ████║██╔════╝
        ██████╔╝█████╗  ███████║██║  ██║ █████╔╝██╔████╔██║█████╗  
        ██╔══██╗██╔══╝  ██╔══██║██║  ██║██╔═══╝ ██║╚██╔╝██║██╔══╝  
        ██║  ██║███████╗██║  ██║██████╔╝███████╗██║ ╚═╝ ██║███████╗
        ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝     ╚═╝╚══════╝

        READ2ME Version 0.1.7 - read the lightning...

    """)
    import uvicorn

    create_or_update_tables()
    try:
        uvicorn.run(
            "main:app", host="0.0.0.0", port=7788, log_config=None, reload=False
        )
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        raise
