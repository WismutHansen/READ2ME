# Read2Me

![READ2ME Banner](Banner.png)

## Overview

Read2Me is a FastAPI application that fetches content from provided URLs, processes the text, converts it into speech using Microsoft Azure's Edge TTS or optionally with the local TTS models StyleTTS2 or Piper TTS, and tags the resulting MP3 files with metadata. The application supports both HTML content and urls pointing to PDF, extracting meaningful text and generating audio files. You can install the provided Chromium Extension in any Chromium-based browser (e.g. Microsoft Edge) to send current urls or any text to the sever, add sources and keywords for automatic fetching.

This is a currently a beta version but I plan to extend it to support other content types (e.g., epub) in the future and provide more robust support for languages other than English. Currently, when using the default Azure Edge TTS, it already supports [other languages](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/ai-services/speech-service/includes/language-support/multilingual-voices.md) and tries to autodetect it from the text but quality might vary depending on the language.

## Features

- Fetches and processes content from HTML URLs and saves it as a markdown file.
- Converts text to speech using Microsoft Azure's Edge TTS (currently randomly selecting from the available multi-lingual voices to easily handle multiple languages).
- Tags MP3 files with metadata, including the title, author, and publication date, if available.
- Adds a cover image with the current date to the MP3 files.
- For urls from wikipedia, uses the wikipedia python library to extract article content
- Automatic retrieval of new articles from specified sources at defined intervals (currently hard coded to twice a day at 5AM and 5PM local time). Sources and keywords can be specified via text files.

## Requirements

- Python 3.7 or higher
- Dependencies listed in `requirements.txt`
- If you want to use the local styleTTS2 text-to-speech model, please also install `requirements_stts2.txt`

## Installation

### Native Python Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/WismutHansen/READ2ME.git
   cd read2me
   ```

2. **Create and activate a virtual environment:**

   ```sh
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

   or if you like to use uv for package management:

   ```sh
   uv venv
   source .venv/bin/activate # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

   if you want to use the local styleTTS2 text-to-speech model, please also install the additional dependencies:

   ```sh
   pip install -r requirements_stts2.txt
   ```

   Install playwright

   ```sh
   playwright install
   ```

  if you want to use piper, run the piperinstal file:

  ```sh
  python3 -m utils.instalpipertts
  ```

   **Note:** [ffmpeg](https://www.ffmpeg.org/) is required when using either StyleTTS2 or PiperTTS for converting wav files into mp3. StyleTTS also requires [espeak-ng](https://github.com/espeak-ng/espeak-ng) to be installed on your system.

4. **Set up environment variables:**

   Rename  `.env.example` file in the root director to `.env` and edit the content to your preference:

   ```sh
   OUTPUT_DIR=Output # Directory to store output files
   SOURCES_FILE=sources.json # File containing sources to retrieve articles from twice a day
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

   **Prepare the environment variables file (.env):**

   copy and rename `.env.example` to `.env`. Edit the content of this file as you wish, specifying the output directory, task file and image path to use for the mp3 file cover as well as the sources and keywords file.

   **Run the FastAPI application:**

   ```sh
   uvicorn main:app --host 0.0.0.0 --port 7777
   ```

   **or, if you're connected to a Linux server e.g. via ssh and want to keep the app running after closing your session**

   ```sh
   nohup uvicorn main:app --host 0.0.0.0 --port 7777 &
   ```

   this will write all commandline output into a file called `nohup.out` in your current working directory.

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

   The repository also contains a working Chromium Extension that you can install in any Chromium-based browser (e.g. Google Chrome) when the developer settings are enabled.

3. **Processing URLs:**

   The application periodically checks the `tasks.json` file for new Jobs to process. It fetches the content for a given url, extracts text, converts it to speech, and saves the resulting MP3 files with appropriate metadata.

4. **Specify Sources and keywords for automatic retrieval:**

Create a file called `sources.json` in your current working directory with URLs to websites that you want to monitor for new articles. You can also set global keywords and per-source keywords to be used as filters for automatic retrieval. If you set "*" for a source, all new articles will be retrieved. Here is an example structure:

```json
{
  "global_keywords": [
    "globalkeyword1",
    "globalkeyword2"
  ],
  "sources": [
    {
      "url": "https://example.com",
      "keywords": ["keyword1","keyword2"]
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

## File Structure

- **main.py**: The main FastAPI application file.
- **requirements.txt**: List of dependencies.
- **.env**: Environment variables file.
- **utils/**: Directory with helper functions for task handling, text extraction, speech synthesis etc.
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
- **newspaper4k**: Library for extracting articles from news websites.
- **wikipedia**: Library for extracting information from Wikipedia articles.
- **schedule**: Library for scheduling tasks. Used to schedule automatic news retrieval twice a day.

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

- [x] language detection and voice selection based on detected language (currently only works for edge-tts).
- [x] Add support for handling of pdf files
- [x] Add support for local text-to-speech (TTS) engine like StyleTTS2.
- [x] Add support for LLM-based text processing like summarization with local LLMs through Ollama or the OpenAI API
- [ ] Add support for automatic image captioning using local vision models or the OpenAI API
- [ ] Add support for F5-TTS

## Acknowledgements

I would like to thank the following repositories and authors for their inspiration and code:

- [stylyetts2](https://github.com/yl4579/StyleTTS2) - One of the best open source TTS engines, and really fast if using NVIDIA/CUDA
- [piperTTS](https://github.com/rhasspy/piper) - Another good local TTS engine that also works on low spec systems
- [AlwaysReddy](https://github.com/ILikeAI/AlwaysReddy) - Thanks to these guys, I got piper TTS working in my project
- [rvc-python](https://pypi.org/project/rvc-python/) - For improving generated speech
- [edge-tts](https://github.com/rany2/edge-tts/tree/master) - Best free online TTS engine
