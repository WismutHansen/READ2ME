import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from utils.env import setup_env
from utils.logging_utils import setup_logging
from utils.task_file_handler import add_task
from utils.task_processor import start_task_processor
from contextlib import asynccontextmanager
from threading import Event

# Load environment variables
output_dir, urls_file, img_pth = setup_env()

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
    try:
        yield
    except Exception as e:
        logging.error(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish
        logging.info("Clean shutdown completed.")

app = FastAPI(lifespan=lifespan)

@app.post("/v1/url/full")
async def url_audio_full(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    add_task('url', request.url, request.tts_engine)
    return {"message": "URL added to the processing list"}

@app.post("/v1/text/full")
async def read_text(request: TextRequest):
    logging.info(f"Received text: {request.text}")
    add_task('text', request.text, request.tts_engine)
    return {"message": "Text added to the processing list"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)