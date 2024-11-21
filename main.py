import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from logging.handlers import TimedRotatingFileHandler
from threading import Event
from typing import List, Optional, Union
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tzlocal import get_localzone

from database.crud import (
    fetch_available_media,
    AvailableMedia,
    get_article,
    get_text,
    get_podcast,
)
from utils.env import setup_env
from utils.history_handler import add_to_history
from utils.source_manager import read_sources, update_sources
from utils.task_file_handler import add_task, get_task_count, get_tasks, remove_task
from utils.task_processor import start_task_processor
from utils.version_check import check_package_versions
from utils.rssfeed import get_articles_from_feed, load_feeds_from_json

# Check package versions
check_package_versions()

# Rest of your main.py code...

# Load environment variables
output_dir, urls_file, img_pth, sources_file = setup_env()

# Background thread stop event
stop_event = Event()


def check_output_dir():
    """
    Checks if the OUTPUT_FOLDER specified in .env exists.
    Creates it if not.

    Returns:
        str: The path to the OUTPUT_FOLDER.
    """
    load_dotenv()

    output_folder = os.getenv("OUTPUT_FOLDER")

    if not output_folder:
        raise ValueError("OUTPUT_FOLDER is not set in the environment variables.")

    # Check if the output folder exists
    if not os.path.exists(output_folder):
        print(f"Output folder '{output_folder}' does not exist. Creating it...")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            raise ValueError(f"Failed to create OUTPUT_FOLDER: {e}")

    return output_folder


def setup_logging(log_file_path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(
        log_file_path, when="midnight", interval=1, backupCount=14
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    logger.addHandler(file_handler)


# Set up logging
try:
    log_file_path = os.path.abspath("process_log.txt")
    setup_logging(log_file_path)
    logging.info("""
      
      ██████╗ ███████╗ █████╗ ██████╗ ██████╗ ███╗   ███╗███████╗
      ██╔══██╗██╔════╝██╔══██╗██╔══██╗╚════██╗████╗ ████║██╔════╝
      ██████╔╝█████╗  ███████║██║  ██║ █████╔╝██╔████╔██║█████╗  
      ██╔══██╗██╔══╝  ██╔══██║██║  ██║██╔═══╝ ██║╚██╔╝██║██╔══╝  
      ██║  ██║███████╗██║  ██║██████╔╝███████╗██║ ╚═╝ ██║███████╗
      ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝     ╚═╝╚══════╝
    
      READ2ME Version 0.1.2 - You' gonna read that?

    """)
    logging.info(f"Logging setup completed. Log file path: {log_file_path}")
except Exception as e:
    print(f"Error setting up logging: {e}")


class URLRequest(BaseModel):
    url: str
    tts_engine: str = "edge"  # Default to edge-tts
    task: Optional[str] = None


class TextRequest(BaseModel):
    text: str
    tts_engine: str = "edge"  # Default to edge-tts
    task: Optional[str] = None


class Source(BaseModel):
    url: str
    keywords: List[str]


class SourceUpdate(BaseModel):
    global_keywords: Optional[List[str]] = None
    sources: Optional[List[Source]] = None


class TaskRemoveRequest(BaseModel):
    type: str
    content: str
    tts_engine: str
    task: Union[str, dict, None] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event.clear()  # Ensure the event is clear before starting the thread
    thread = start_task_processor(stop_event)
    scheduler_task = asyncio.create_task(schedule_fetch_articles())
    articles_cache_task = asyncio.create_task(start_articles_cache_refresh())
    try:
        yield
    except Exception as e:
        logging.error(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish
        scheduler_task.cancel()  # Cancel the scheduler task
        articles_cache_task.cancel()  # Cancel the articles cache refresh task
        try:
            await scheduler_task  # Wait for the scheduler task to finish
            await (
                articles_cache_task
            )  # Wait for the articles cache refresh task to finish
        except asyncio.CancelledError:
            logging.info("Scheduler task cancelled.")
            logging.info("Articles cache refresh task cancelled.")
        logging.info("Clean shutdown completed.")


app = FastAPI(
    lifespan=lifespan,
    title="Read2Me API",
    description="API for text-to-speech conversion and more",
    version="0.1.2",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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
    task_dict = task.model_dump()
    existing_tasks = await get_tasks()

    if task_dict not in existing_tasks:
        raise HTTPException(status_code=404, detail="Task not found in queue")

    await remove_task(task_dict)
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

    await add_task("url", request.url, request.tts_engine, "full")
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
    await add_task("url", request.url, request.tts_engine, "story")
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
    await add_task("url", request.url, request.tts_engine, task="tldr")
    return {"message": "URL/Summary added to the READ2ME task list"}


@app.post("/v1/text/full")
async def read_text(request: TextRequest):
    logging.info(f"Received text: {request.text}")
    await add_task("text", request.text, request.tts_engine, task="full")
    return {"message": "Text added to the READ2ME task list"}


@app.post("/v1/text/summary")
async def read_text_summary(request: TextRequest):
    logging.info("Received task text/summary}")
    logging.info(
        f"URL type: {type(request.text)}, TTS Engine type: {type(request.tts_engine)}, task: summary"
    )

    await add_task("text", request.text, request.tts_engine, task="tldr")
    return {"message": "text/summary added to the READ2ME task list"}


@app.post("/v1/text/podcast")
async def read_text_podcast(request: TextRequest):
    logging.info("Received task text/podcast}")
    logging.info(
        f"URL type: {type(request.text)}, TTS Engine type: {type(request.tts_engine)}, task: podcast"
    )

    await add_task("text", request.text, request.tts_engine, task="podcast")
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
    try:
        sources = (
            [
                {"url": source.url, "keywords": source.keywords}
                for source in update.sources
            ]
            if update.sources
            else None
        )
        updated_data = update_sources(update.global_keywords, sources)
        return {"message": "Sources updated successfully", "data": updated_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/sources/get")
async def api_get_sources():
    return read_sources()


# New endpoint to force re-process a URL in case of e.g. a change in the source
@app.post("/v1/url/reprocess")
async def url_audio_reprocess(request: URLRequest):
    logging.info(f"Reprocessing URL: {request.url}")
    await add_to_history(request.url)  # Add to history to avoid future re-processing
    await add_task("url", request.url, request.tts_engine)
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


# @app.get("/v1/articles")
# async def get_articles(request: Request, page: int = 1, limit: int = 20):
#    articles = []
#    total_articles = 0
#
#    for root, dirs, files in os.walk(output_dir, topdown=False):
#        date_folder = os.path.basename(root)
#        if not date_folder.isdigit() or len(date_folder) != 8:
#            continue  # Skip if not a date folder
#
#        for file in files:
#            if file.endswith(".mp3"):
#                total_articles += 1
#                if (page - 1) * limit <= len(articles) < page * limit:
#                    article_id = generate_article_id(date_folder, file)
#                    relative_path = get_relative_path(
#                        os.path.join(root, file)
#                    )
#                    audio_url = f"/v1/audio/{relative_path}"
#                    articles.append(
#                        {
#                            "id": article_id,
#                            "date": date_folder,
#                            "audio_file": audio_url,
#                            "title": os.path.splitext(file)[0].replace("_", " "),
#                        }
#                    )
#
#                if len(articles) >= limit:
#                    break
#
#        if len(articles) >= limit:
#            break
#
#    return JSONResponse(
#        content={
#            "articles": articles,
#            "total_articles": total_articles,
#            "page": page,
#            "limit": limit,
#            "total_pages": (total_articles + limit - 1) // limit,
#        }
#    )


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


async def schedule_fetch_articles():
    from utils.sources import fetch_articles

    async def job():
        logging.info("Fetching articles...")
        await fetch_articles()

    local_tz = get_localzone()
    logging.info(f"Using local timezone: {local_tz}")

    while not stop_event.is_set():
        now = datetime.now(local_tz)
        target_times = [
            time(5, 0),
            time(12, 0),
            time(19, 0),
        ]  # 6:00 AM, 12:00 PM and 7:00 PM

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


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="0.0.0.0", port=7777, log_config=None)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        raise
