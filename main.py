import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from utils.env import setup_env
from utils.logging_utils import setup_logging
from utils.task_file_handler import add_task
from utils.task_processor import start_task_processor
from contextlib import asynccontextmanager
from threading import Event
import asyncio
from datetime import datetime, time, timedelta
from tzlocal import get_localzone

# Load environment variables
output_dir, urls_file, img_pth, sources_file, keywords_file = setup_env()

# Set up logging
setup_logging("process_log.txt")

# Background thread stop event
stop_event = Event()

class URLRequest(BaseModel):
    url: str
    tts_engine: str = "edge"  # Default to edge-tts

class TextRequest(BaseModel):
    text: str
    tts_engine: str = "edge"  # Default to edge-tts

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

@app.post("/v1/url/full")
async def url_audio_full(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    add_task("url", request.url, request.tts_engine)
    return {"URL added to the READ2ME task list"}

@app.post("/v1/url/summary")
async def url_audio_summary(request: URLRequest):
    return {"Endpoint not yet implemented"}

@app.post("/v1/text/full")
async def read_text(request: TextRequest):
    logging.info(f"Received text: {request.text}")
    add_task("text", request.text, request.tts_engine)
    return {"Text added to the READ2ME task list"}

@app.post("/v1/text/summary")
async def read_text_summary(request: TextRequest):
    return {"Endpoint not yet implemented"}

@app.post("/v1/sources/fetch")
async def fetch_sources(request: Request):
    from utils.sources import fetch_articles
    await fetch_articles()
    logging.info(f"Received manual article fetch request")
    return {"message": "Checking for new articles in sources"}

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
                next_run = now.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)
                break
        else:
            next_run = now.replace(hour=target_times[0].hour, minute=target_times[0].minute, second=0, microsecond=0)
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        logging.info(f"Next scheduled run at {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
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
    uvicorn.run(app, host="0.0.0.0", port=7777)
