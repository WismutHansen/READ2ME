import sys
import os
import logging
from utils.common_utils import shorten_text, split_text, write_markdown_file, sanitize_filename
from dotenv import load_dotenv
from .Local_Ollama import ask_Ollama
from .Local_OpenAI import ask_LLM
from .Prompts import pod, title_prompt, story_mode, markdown
# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()


def llm_call(prompt: str) -> str:
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
        prompt = f"{short_text} +{title_prompt}"

        title = llm_call(prompt)
        title = sanitize_filename(title)
        return title

    except Exception as e:
        logging.error(f"Title Generation failed, returning empty string: {e}")
        return ""


def tldr(text):
    try:
        chunks = split_text(text, max_words=64000)
        summaries = []

        logging.debug(f"Number of chunks: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            logging.debug(
                f"Processing chunk {i + 1}/{len(chunks)} with {len(chunk.split())} words"
            )
            prompt = f"{chunk}\n--------\nReturn a concise summary for the above text, without referencing the text or mentioning 'in the text' or similar phrases. Keep the tone and perspective of the original text."

            summary = llm_call(prompt)

            logging.debug(f"Generated summary for chunk {i + 1}/{len(chunks)}")
            summaries.append(summary)

        return " ".join(summaries)
    except Exception as e:
        logging.error(f"Summary Generation failed, returning empty string: {e}")
        return ""


def podcast(text: str) -> tuple[str, str]:
    prompt = f"{text} + {pod}"
    script = llm_call(prompt)
    title = generate_title(script)
    write_markdown_file(title + ".md", script)
    return script, title


def story(text: str, language: str = "en-US"):
    prompt = f"{text} + {story_mode} + In {language}"
    script = llm_call(prompt)
    write_markdown_file("story.md", script)
    return script


def to_markdown(text: str) -> str:
    prompt = f"{text} + {markdown}"
    markdown_text = llm_call(prompt)
    return markdown_text


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
