import sys
import os
from utils.common_utils import shorten_text
from dotenv import load_dotenv
from .Local_Ollama import ask_Ollama
from .Local_OpenAI import ask_LLM
import logging


load_dotenv()

def generate_title(text):
    
    try:
        short_text = shorten_text(text)
        prompt = f"{short_text}\n--------\nReturn a concise, 3-5 word phrase as the title for the above text, strictly adhering to the 3-5 word limit and avoiding the use of the word 'title'"
        if os.getenv('LLM_ENGINE') == "Ollama":
            title = ask_Ollama(prompt)
        elif os.getenv('LLM_ENGINE') == "OpenAI":
            title = ask_LLM(prompt)       
        else:
            logging.error(f"Unsupported or unavailable LLM_engine")
            return ""
        return title

    except Exception as e:
        logging.error(f"Title Generation failed, returning empty string: {e}")
        return ""
    
if __name__ == "__main__":
    text = input("Enter the text to be used for title generation: ")
    if text:
        print(generate_title(text))
    else:
        logging.error("No text provided, returning empty string.")