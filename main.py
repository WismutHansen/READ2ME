import logging
from fastapi import FastAPI, Request, UploadFile, HTTPException, File, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from utils.env import setup_env
from utils.logging_utils import setup_logging
from utils.task_file_handler import add_task
from utils.task_processor import start_task_processor
from utils.source_manager import update_sources, read_sources
from urllib.parse import unquote
from contextlib import asynccontextmanager
from threading import Event
import asyncio
from datetime import datetime, time, timedelta
from tzlocal import get_localzone
from logging.handlers import TimedRotatingFileHandler
from typing import List, Optional
import sys
import os

# Load environment variables
output_dir, urls_file, img_pth, sources_file = setup_env()

# Background thread stop event
stop_event = Event()


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


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="Output"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/v1/url/full")
async def url_audio_full(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    await add_task("url", request.url, request.tts_engine)
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
        sources = [{"url": source.url, "keywords": source.keywords} for source in update.sources] if update.sources else None
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
async def get_audio_files():
    output_dir = os.getenv("OUTPUT_DIR", "Output")
    audio_files = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith(".mp3"):
                relative_path = os.path.relpath(os.path.join(root, file), output_dir)
                audio_files.append({
                    "audio_file": f"static/{relative_path.replace(os.sep, '/')}",
                    "title": os.path.splitext(file)[0].replace("_", " ")
                })
    return JSONResponse(content={"audio_files": audio_files})

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
        raise HTTPException(status_code=404, detail=f"Text file not found: {text_file_path}")
    
    try:
        with open(text_file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return JSONResponse(content={"text": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

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




async def schedule_fetch_articles():
    from utils.sources import fetch_articles

    async def job():
        logging.info("Fetching articles...")
        await fetch_articles()

    local_tz = get_localzone()
    logging.info(f"Using local timezone: {local_tz}")

    while not stop_event.is_set():
        now = datetime.now(local_tz)
        target_times = [time(6, 0), time(17, 0)]  # 6:00 AM and 5:00 PM

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
