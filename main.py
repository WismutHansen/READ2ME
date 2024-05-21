import logging
from fastapi import FastAPI
from pydantic import BaseModel
from utils.env import setup_env
from utils.logging_utils import setup_logging
from utils.url_processing import process_urls, add_url_to_file
from contextlib import asynccontextmanager
from threading import Thread, Event

# Load environment variables
output_dir, urls_file, img_pth = setup_env()

# Set up logging
setup_logging("process_log.txt")

# Background thread stop event
stop_event = Event()

class URLRequest(BaseModel):
    url: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event.clear()  # Ensure the event is clear before starting the thread
    thread = Thread(target=process_urls, args=(urls_file, stop_event, output_dir, img_pth))
    thread.daemon = True
    thread.start()
    try:
        yield
    except Exception as e:
        logging.error(f"Unhandled exception during server lifecycle: {e}")
    finally:
        stop_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to finish
        logging.info("Clean shutdown completed.")

app = FastAPI(lifespan=lifespan)

@app.post("/synthesize/")
async def synthesize(request: URLRequest):
    logging.info(f"Received URL: {request.url}")
    add_url_to_file(request.url, urls_file)
    return {"message": "URL added to the processing list"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
