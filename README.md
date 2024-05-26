# Read2Me

![READ2ME Cover Image Depicting a black and white grainy photo of a pair of overear headphones. Image Caption reades: READ2ME. The image was generated with Dall-E 3 from OpenAI](front.jpg)

## Overview

Read2Me is a FastAPI application that fetches content from provided URLs, processes the text, converts it into speech using Microsoft Azure's Edge TTS, and tags the resulting MP3 files with metadata. The application supports both HTML content types, extracting meaningful text and generating audio files.

This is a first alpha version but I plan to extend it to support other content types (e.g., PDF) in the future and provide more robust support for languages other than English.

## Features

- Fetches and processes content from HTML URLs and saves it as a markdown file.
- Converts text to speech using Microsoft Azure's Edge TTS (currently randomly selecting from the available multi-lingual voices to easily handle multiple languages).
- Tags MP3 files with metadata, including the title, author, and publication date, if available.
- Adds a cover image with the current date to the MP3 files.

## Requirements

- Python 3.7 or higher
- Dependencies listed in `requirements.txt`

## Installation

### Native Python Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/WismutHansen/READ2ME.git
   cd read2me
   ```

2. **Create and activate a virtual environment:**

   ```sh
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Rename  `.env.example` file in the root director to `.env` and edit the content to your preference:

   ```sh
   OUTPUT_DIR=Output # Directory to store output files
   TASK_FILE=tasks.txt # File containing URLs to process
   IMG_PATH=front.jpg # Path to image file to use as cover
   ```
### Docker Installation

   **Build the Docker image**
   ```sh
   docker build -t read2me .
   ```


## Usage

1. 
   ### Native 
   **Run the FastAPI application:**

   ```sh
   uvicorn main:app --host 0.0.0.0 --port 7777
   ```
   ### Docker



   **Run the Docker container (with a volume mount if you want to access the Output Folder from outside the container):**

   ```sh
   docker run -p 7777:7777 -v /path/to/local/output/dir:/app/Output read2me
   ```


2. **Add URLs for processing:**

   Send a POST request to `http://localhost:7777/v1/url/full` with a JSON body containing the URL:

   ```json
   {
     "url": "https://example.com/article"
   }
   ```

   You can use `curl` or any API client like Postman to send this request like this:

   ```sh
   curl -X POST http://localhost:7777/v1/url/full/ \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/article"}'
     -d '{"tts-engine": "edge"}'
   ```

3. **Processing URLs:**

   The application periodically checks the `tasks.txt` file for new URLs to process. It fetches the content, extracts text, converts it to speech, and saves the resulting MP3 files with appropriate metadata.

## API Endpoints

- **POST /v1/url/full**

  Adds a URL to the processing list.

  **Request Body:**

  ```json
  {
    "url": "https://example.com/article",
    "tts-engine": "edge"
  }
  ```

  **Response:**

  ```json
  {
    "message": "URL added to the processing list"
  }
  ```

## File Structure

- **main.py**: The main FastAPI application file.
- **requirements.txt**: List of dependencies.
- **.env**: Environment variables file.
- **Output/**: Directory where the output files (MP3 and MD) are saved.

## Dependencies

- **FastAPI**: Web framework for building APIs.
- **Uvicorn**: ASGI server implementation for serving FastAPI applications.
- **edge-tts**: Microsoft Azure Edge Text-to-Speech library.
- **mutagen**: Library for handling audio metadata.
- **Pillow**: Python Imaging Library (PIL) for image processing.
- **trafilatura**: Library for web scraping and text extraction.
- **requests**: HTTP library for sending requests.
- **BeautifulSoup**: Library for parsing HTML and XML documents.
- **pdfminer**: Library for extracting text from PDF documents.
- **python-dotenv**: Library for managing environment variables.

## Contributing

1. **Fork the repository.**
2. **Create a new branch:**

   ```sh
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes and commit them:**

   ```sh
   git commit -m 'Add some feature'
   ```

4. **Push to the branch:**

   ```sh
   git push origin feature/your-feature-name
   ```

5. **Submit a pull request.**

## License

This project is licensed under the Apache License Version 2.0, January 2004, except for the styletts2 code, which is licensed under the MIT License. The styletts2 pre-trained models are under their own license.

StyleTTS2 Pre-Trained Models: Before using these pre-trained models, you agree to inform the listeners that the speech samples are synthesized by the pre-trained models, unless you have the permission to use the voice you synthesize. That is, you agree to only use voices whose speakers grant the permission to have their voice cloned, either directly or by license before making synthesized voices public, or you have to publicly announce that these voices are synthesized if you do not have the permission to use these voices.

## Roadmap

- [ ] language detection and voice selection based on detected language.
- [ ] Add support for handling of pdf files
- [x] Add support for local text-to-speech (TTS) engine like StyleTTS2.
- [ ] Add support for LLM-based text processing like summarization with local LLMs through Ollama or the OpenAI API
- [ ] Add support for automatic image captioning using local vision models or the OpenAI API





