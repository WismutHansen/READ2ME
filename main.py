import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from logging.handlers import TimedRotatingFileHandler
from threading import Event
from typing import List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tzlocal import get_localzone

from database.crud import fetch_available_media, AvailableMedia
from utils.env import setup_env
from utils.history_handler import add_to_history
from utils.logging_utils import setup_logging
from utils.source_manager import read_sources, update_sources
from utils.task_file_handler import add_task
from utils.task_processor import start_task_processor
from utils.version_check import check_package_versions

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


class TextRequest(BaseModel):
    text: str
    tts_engine: str = "edge"  # Default to edge-tts


class Source(BaseModel):
    url: str
    keywords: List[str]


class SourceUpdate(BaseModel):
    global_keywords: Optional[List[str]] = None
    sources: Optional[List[Source]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event.clear()  # Ensure the event is clear before starting the thread
    thread = start_task_processor(stop_event)
    scheduler_task = asyncio.create_task(schedule_fetch_articles())
    try:
        yield
    except Exception as e:
        logging.error(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish
        scheduler_task.cancel()  # Cancel the scheduler task
        try:
            await scheduler_task  # Wait for the scheduler task to finish
        except asyncio.CancelledError:
            logging.info("Scheduler task cancelled.")
        logging.info("Clean shutdown completed.")


app = FastAPI(
    lifespan=lifespan,
    title="Read2Me API",
    description="API for text-to-speech conversion and more",
    version="0.1.2",
)

# Update this line to use an absolute path
# output_dir = os.path.abspath(os.getenv("OUTPUT_DIR", "Output"))

# Mount the static files with the correct directory
app.mount("/static", StaticFiles(directory=output_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],  # Update with the frontend URL if different from the standard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    await add_task("url", request.url, request.tts_engine)
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
    await add_task("podcast", request.url, request.tts_engine)
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
    await add_task("story", request.url, request.tts_engine)
    return {"message": "URL added to the READ2ME task list"}


@app.post("/v1/url/summary")
async def url_audio_summary(request: URLRequest):
    return {"message": "Endpoint not yet implemented"}


@app.post("/v1/text/full")
async def read_text(request: TextRequest):
    logging.info(f"Received text: {request.text}")
    await add_task("text", request.text, request.tts_engine)
    return {"message": "Text added to the READ2ME task list"}


@app.post("/v1/text/summary")
async def read_text_summary(request: TextRequest):
    return {"message": "Endpoint not yet implemented"}


@app.post("/v1/pdf/full")
async def read_text_summary(request: TextRequest):
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
                    relative_path = os.path.relpath(
                        os.path.join(root, file), output_dir
                    )
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
    full_path = os.path.join(output_dir, file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(full_path, media_type="audio/mpeg")


@app.get("/v1/audio-file/{file_name}")
async def get_audio_file(file_name: str):
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    md_file_path = os.path.join("", f"{file_name}.md")
    if not os.path.exists(md_file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(md_file_path, "r", encoding="utf-8") as file:
        text_content = file.read()
    return JSONResponse(content={"text": text_content})


@app.get("/v1/audio-file/{title}")
async def get_audio_file_text(title: str):
    # Assuming the text files are stored in the Output directory with the same name as the title
    text_file_path = os.path.join("", f"{title}.md")

    if not os.path.isfile(text_file_path):
        raise HTTPException(status_code=404, detail="Text file not found")

    with open(text_file_path, "r") as file:
        text = file.read()

    return {"text": text}


@app.get("/v1/audio-file/{file_path:path}")
async def get_audio_file_text(file_path: str):
    # Normalize the file path to use the correct directory separator
    file_path = os.path.normpath(file_path)

    # Construct the full path to the text file
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    text_file_path = os.path.join(output_dir, f"{file_path}.md")

    if not os.path.isfile(text_file_path):
        raise HTTPException(
            status_code=404, detail=f"Text file not found: {text_file_path}"
        )

    try:
        with open(text_file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return JSONResponse(
            content={
                "text": text,
                "title": os.path.basename(file_path),
                "audio_file": f"{file_path}.mp3",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# Endpoint for fetching the VTT file
@app.get("/v1/vtt-file/{file_path:path}")
async def get_vtt_file(file_path: str):
    # Normalize the file path to use the correct directory separator
    file_path = os.path.normpath(file_path)

    # Construct the full path to the VTT file
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    vtt_file_path = os.path.join(output_dir, f"{file_path}.vtt")

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


@app.get("/v1/articles")
async def get_articles(request: Request, page: int = 1, limit: int = 20):
    articles = []
    total_articles = 0

    for root, dirs, files in os.walk(output_dir, topdown=False):
        date_folder = os.path.basename(root)
        if not date_folder.isdigit() or len(date_folder) != 8:
            continue  # Skip if not a date folder

        for file in files:
            if file.endswith(".mp3"):
                total_articles += 1
                if (page - 1) * limit <= len(articles) < page * limit:
                    article_id = generate_article_id(date_folder, file)
                    relative_path = os.path.relpath(
                        os.path.join(root, file), output_dir
                    )
                    audio_url = f"/v1/audio/{relative_path}"
                    articles.append(
                        {
                            "id": article_id,
                            "date": date_folder,
                            "audio_file": audio_url,
                            "title": os.path.splitext(file)[0].replace("_", " "),
                        }
                    )

                if len(articles) >= limit:
                    break

        if len(articles) >= limit:
            break

    return JSONResponse(
        content={
            "articles": articles,
            "total_articles": total_articles,
            "page": page,
            "limit": limit,
            "total_pages": (total_articles + limit - 1) // limit,
        }
    )


@app.get("/v1/article/{article_id}")
async def get_article(article_id: str):
    date_folder, file_prefix = article_id.split("_")

    for root, dirs, files in os.walk(os.path.join(output_dir, date_folder)):
        for file in files:
            if (
                file.endswith(".mp3")
                and generate_article_id(date_folder, file) == article_id
            ):
                relative_path = os.path.relpath(os.path.join(root, file), output_dir)
                audio_url = f"/v1/audio/{relative_path}"
                text_file_path = os.path.join(root, f"{os.path.splitext(file)[0]}.md")

                if not os.path.isfile(text_file_path):
                    raise HTTPException(
                        status_code=404, detail="Article text not found"
                    )

                with open(text_file_path, "r", encoding="utf-8") as text_file:
                    content = text_file.read()

                return JSONResponse(
                    content={
                        "id": article_id,
                        "date": date_folder,
                        "audio_file": audio_url,
                        "title": os.path.splitext(file)[0].replace("_", " "),
                        "content": content,
                    }
                )

    raise HTTPException(status_code=404, detail="Article not found")


@app.get("/v1/available-media", response_model=List[AvailableMedia])
async def get_available_media():
    media = fetch_available_media()
    if not media:
        raise HTTPException(
            status_code=404, detail="No available media with audio found."
        )
    return media


@app.get("/v1/server/status")
async def get_status():
    return {"message": "Endpoint not yet implemented"}


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


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="0.0.0.0", port=7777, log_config=None)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        raise
