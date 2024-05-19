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

   Create a `.env` file in the root directory of the project with the following content:

   ```sh
   OUTPUT_DIR=Output # Directory to store output files
   URL_FILE=urls.txt # File containing URLs to process
   IMG_PATH=front.jpg # Path to image file to use as cover
   ```

## Usage

1. **Run the FastAPI application:**

   ```sh
   python app.py
   ```

2. **Add URLs for processing:**

   Send a POST request to `http://localhost:7777/synthesize/` with a JSON body containing the URL:

   ```json
   {
     "url": "https://example.com/article"
   }
   ```

   You can use `curl` or any API client like Postman to send this request like this:

   ```sh
   curl -X POST http://localhost:7777/synthesize/ \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/article"}'
   ```

3. **Processing URLs:**

   The application periodically checks the `urls.txt` file for new URLs to process. It fetches the content, extracts text, converts it to speech, and saves the resulting MP3 files with appropriate metadata.

## API Endpoints

- **POST /synthesize/**

  Adds a URL to the processing list.

  **Request Body:**

  ```json
  {
    "url": "https://example.com/article"
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

This project is licensed under the Apache License Version 2.0, January 2004

## Roadmap

- [ ] language detection and voice selection based on detected language.
- [ ] Add support for handling of pdf files
- [ ] Add support for local text-to-speech (TTS) engine like StyleTTS2.
- [ ] Add support for LLM-based text processing like summarization with local LLMs through Ollama or the OpenAI API
- [ ] Add support for automatic image captioning using local vision models or the OpenAI API





