import re
from ollama import Client
from dotenv import load_dotenv
from .text_processing import remove_think_tags
import os

load_dotenv()
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
model_name = os.getenv("MODEL_NAME", "llama3.2:latest")


def ask_Ollama(user_message, system_message="You are a helpful assistant"):
    client = Client(host=ollama_base_url)
    stream = client.chat(
        model=model_name,
        messages=[{"role": "user", "content": user_message}],
        stream=True,
        keep_alive="0",
    )

    response = ""
    for chunk in stream:
        response += chunk["message"]["content"]

    if "deepseek-r1" in model_name:  # we remove the <think> tags if using deepseek-r1
        response = remove_think_tags(response)
    return response


if __name__ == "__main__":
    history = ""
    while True:
        question = input("\n\nYou\n--------\n")
        if history == "":
            answer = ask_Ollama(question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
        else:
            answer = ask_Ollama(history + question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
        history += f"User: {question}\nAssistant: {answer}\n"
