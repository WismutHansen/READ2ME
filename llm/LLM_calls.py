import sys
import os
import logging
from utils.common_utils import shorten_text, split_text, write_markdown_file
from dotenv import load_dotenv

from langchain_core.output_parsers import JsonOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from typing import Literal

from .Local_Ollama import ask_Ollama
from .Local_OpenAI import ask_LLM
from .Prompts import pod, title_prompt, story_mode, summ_prompt, story_mode_with_language

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()


class PodcastLine(BaseModel):
    speaker: Literal['man', 'woman'] = Field(
        description='Indicates the gender of the speaker in this podcast line. Acceptable values are "man" or "woman"')
    text: str = Field(description='The text of the podcast line')


class Podcast(BaseModel):
    podcast: list[PodcastLine] = Field(description="List of podcast lines")


def llm_call(prompt) -> str:
    llm_engine = os.getenv("LLM_ENGINE")
    logging.debug(f"LLM_ENGINE: {llm_engine}")

    if llm_engine == "Ollama":
        response = ask_Ollama(prompt)
    elif llm_engine == "OpenAI":
        response = ask_LLM(prompt)
    else:
        logging.error("Unsupported or unavailable LLM_engine")
        return ""
    return response


def generate_title(text):
    try:
        short_text = shorten_text(text)
        prompt = title_prompt.format(text=short_text)

        title = llm_call(prompt)
        return title

    except Exception as e:
        logging.error(f"Title Generation failed, returning empty string: {e}")
        return ""


def tldr(text):
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=20,
            length_function=len,
            is_separator_regex=False
        )

        chunks = text_splitter.split_text(text)
        print(len(chunks))
        summaries = []

        logging.debug(f"Number of chunks: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            logging.debug(
                f"Processing chunk {i + 1}/{len(chunks)} with {len(chunk.split())} words"
            )
            prompt = summ_prompt.format(text=chunk)

            summary = llm_call(prompt)

            logging.debug(f"Generated summary for chunk {i + 1}/{len(chunks)}")
            summaries.append(summary)

        return " ".join(summaries)
    except Exception as e:
        logging.error(f"Summary Generation failed, returning empty string: {e}")
        return ""


def podcast(text: str) -> str:
    parser = JsonOutputParser(pydantic_object=Podcast)
    prompt = pod.format(text=text, format_instructions=parser.get_format_instructions())
    script = llm_call(prompt)
    parsed_script = parser.parse(script)
    message = ""
    for line in parsed_script["podcast"]:
        message_line = f"{line['speaker']}: {line['text']}"
        message += message_line + "\n\n"
    write_markdown_file("podcast.md", message)
    return script


def story(text: str, language: str = "en-US"):
    prompt = story_mode_with_language.format(text=text, language=language)
    script = llm_call(prompt)
    write_markdown_file("story.md", script)
    return script


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.error("Usage: python script_name.py <path_to_md_file>")
        print("Usage: python script_name.py <path_to_md_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        print(f"File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        if text:
            logging.info("File read successfully, generating summary...")
            result = podcast(text)
            print(result)
        else:
            logging.error("No text found in the file, returning empty string.")
            print("No text found in the file")
    except Exception as e:
        logging.error(f"Failed to read file: {e}")
        print(f"Failed to read file: {e}")
        sys.exit(1)
