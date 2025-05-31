# Read2Me

![READ2ME Banner](Banner.png)

## Overview

Read2Me is a FastAPI application that fetches content from provided URLs, processes the text, converts it into speech using Microsoft Azure's Edge TTS or with the local TTS models Kokoro TTS (via Kokoro FastAPI), or chatterbox, and tags the resulting MP3 files with metadata. You can either turn the full text into audio or have an LLM convert the seed text into a podcast. Currently Ollama and any OpenAI compatible API is supported. You can install the provided Chromium Extension in any Chromium-based browser (e.g. Chrome or Microsoft Edge) to send current urls or any text to the sever, add sources and keywords for automatic fetching.

This is a currently a beta version but I plan to extend it to support other content types (e.g., epub) in the future and provide more robust support for languages other than English. Currently, when using the default Azure Edge TTS, it already supports [other languages](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/ai-services/speech-service/includes/language-support/multilingual-voices.md) and tries to autodetect it from the text but quality might vary depending on the language.

## Features

- Fetches and processes content from HTML URLs and saves it as a markdown file.
- Converts text to speech using Microsoft Azure's Edge TTS (currently randomly selecting from the available multi-lingual voices to easily handle multiple languages).
- Tags MP3 files with metadata, including the title, author, and publication date, if available.
- Adds a cover image with the current date to the MP3 files.
- For urls from wikipedia, uses the wikipedia python library to extract article content
- Automatic retrieval of new articles from specified sources at defined intervals (currently hard coded to twice a day at 5AM and 5PM local time). Sources and keywords can be specified via text files.
- Turn any seed text (url or manually entered text) into a podcast
- Chrome Extension available on the Chrome WebStore: [READ2ME Browser Companion](https://chromewebstore.google.com/detail/read2me-browser-companion/khbimiljkjbgnphmpeoimkppidmgnelb). If you prefer installing the Extension from source, it's available in this repository as well.

## Requirements

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for python package management
- [pnpm](https://pnpm.io/) for javascript package management

## Installation

### FastAPI backend

1. **Clone the repository:**

   ```sh
   git clone https://github.com/WismutHansen/READ2ME.git
   cd read2me
   ```

2. **Install python dependencies**

   ```bash
   uv sync # Replace name with the name of the script you want to run
   ```

3. **Activate venv and install playwright**
   Install playwright

   ```sh
   source .venv/bin/activate && playwright install # or .venv\Scripts\activate && playwright install (on Windows)
   ```

**Note:** [ffmpeg](https://www.ffmpeg.org/) is required when using either for converting wav files into mp3.

4. **Set up environment variables:**

   Rename `.env.example` file in the root director to `.env` and edit the content to your preference:

   ```sh
   OUTPUT_DIR=Output # Directory to store output files
   SOURCES_FILE=sources.json # File containing sources to retrieve articles from twice a day
   IMG_PATH=front.jpg # Path to image file to use as cover
   OLLAMA_BASE_URL=http://localhost:11434    # Standard Port for Ollama
   OPENAI_BASE_URL=http://localhost:11434/v1 # Example for Ollama Open AI compatible endpoint
   OPENAI_API_KEY=skxxxxxx                   # Your OpenAI API Key in case of using the official OpenAI API
   MODEL_NAME=llama3.2:latest
   LLM_ENGINE=Ollama #Valid Options: Ollama, OpenAI
   ```

   You can use either Ollama or any OpenAI compatible API for title and podcast script generation (summary function also coming soon)

5. **Start the backend**

   ```bash
   uv run main.py
   ```

### Next.js frontend

```bash
 cd frontend && cp .env.local.example .env.local && pnpm install && pnpm run dev
```

you can access the frontend on <http://localhost:3000>

## **Add URLs for processing without frontend:**

Send a POST request to `http://localhost:7788/v1/url/full` with a JSON body containing the URL:

```json
{
  "url": "https://example.com/article"
}
```

You can use `curl` or any API client like Postman to send this request like this:

```sh
curl -X POST http://localhost:7788/v1/url/full/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
  -d '{"tts-engine": "edge"}'
```

The repository also contains a working Chromium Extension that you can install in any Chromium-based browser (e.g. Google Chrome) when the developer settings are enabled.

3. **Processing URLs:**

   The application periodically checks the `tasks.json` file for new Jobs to process. It fetches the content for a given url, extracts text, converts it to speech, and saves the resulting MP3 files with appropriate metadata.

4. **Specify Sources and keywords for automatic retrieval:**

Create a file called `sources.json` in your current working directory with URLs to websites that you want to monitor for new articles. You can also set global keywords and per-source keywords to be used as filters for automatic retrieval. If you set "\*" for a source, all new articles will be retrieved. Here is an example structure:

```json
{
  "global_keywords": ["globalkeyword1", "globalkeyword2"],
  "sources": [
    {
      "url": "https://example.com",
      "keywords": ["keyword1", "keyword2"]
    },
    {
      "url": "https://example2.com",
      "keywords": ["*"]
    }
  ]
}
```

Location of both files is configurable in .env file.

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

- **POST /v1/url/podcast**
- **POST /v1/text/full**
- **POST /v1/text/podcast**

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
- **newspaper4k**: Library for extracting articles from news websites.
- **wikipedia**: Library for extracting information from Wikipedia articles.
- **schedule**: Library for scheduling tasks. Used to schedule automatic news retrieval twice a day.
- and many more but I plan on reducing the dependencies a bit by removing redundancies etc.

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

- [x] language detection and voice selection based on detected language (currently only works for edge-tts).
- [x] Add support for handling of pdf files
- [x] Add support for LLM-based text processing like podcast transcript with local LLMs through Ollama or the OpenAI API
- [x] Add support for chatterbox TTS
- [ ] Add support for automatic image captioning using local vision models or the OpenAI API

## Acknowledgements

I would like to thank the following repositories and authors for their inspiration and code:

- [F5-TTS](https://github.com/PasiKoodaa/F5-TTS.git) - A great open weights TTS model!
- [stylyetts2](https://github.com/yl4579/StyleTTS2) - A great open source TTS engine, and really fast if using NVIDIA/CUDA
- [piperTTS](https://github.com/rhasspy/piper) - Another good local TTS engine that also works on low spec systems
- [AlwaysReddy](https://github.com/ILikeAI/AlwaysReddy) - Thanks to these guys, I got piper TTS working in my project (now removed due to better TTS models available)
- [rvc-python](https://pypi.org/project/rvc-python/) - For improving generated speech
- [edge-tts](https://github.com/rany2/edge-tts/tree/master) - Best free online TTS engine
- [kokoro tts](https://huggingface.co/hexgrad/Kokoro-82M) - The fastest local TTS model with awesome audio quality!
- [kokoro FastAPI](https://github.com/remsky/Kokoro-FastAPI) - OpenAI-API compatible FastAPI server for Kokoro TTS
- [chatterbox](https://github.com/resemble-ai/chatterbox) - The best TTS model for English by far (in May 2025) thanks to the great work by resemble.ai!
