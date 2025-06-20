from ollama import Client
from dotenv import load_dotenv
from .text_processing import remove_think_tags
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
model_name = os.getenv("MODEL_NAME", "llama3.2:latest")
LOW_VRAM = os.environ.get("LOW_VRAM", False)

# Global variable to track model loading state
ollama_model_loaded = False


def ask_Ollama(user_message, system_message="You are a helpful assistant"):
    global ollama_model_loaded
    client = Client(host=ollama_base_url)

    keep_alive_duration = "0s" if LOW_VRAM else "5m"

    if not ollama_model_loaded:
        logger.info(
            f"Ollama model '{model_name}' is not loaded. Loading with keep_alive='{keep_alive_duration}'."
        )
        # The model loads on the first call to client.chat()
        # We set the flag here, actual loading is handled by Ollama server based on keep_alive
        ollama_model_loaded = True
    else:
        logger.info(
            f"Ollama model '{model_name}' is already loaded. Using keep_alive='{keep_alive_duration}'."
        )

    stream = client.chat(
        model=model_name,
        messages=[{"role": "user", "content": user_message}],
        stream=True,
        options={"keep_alive": keep_alive_duration},  # Pass keep_alive in options
    )

    response = ""
    for chunk in stream:
        response += chunk["message"]["content"]

    if "deepseek-r1" in model_name:  # we remove the <think> tags if using deepseek-r1
        response = remove_think_tags(response)
    return response


def unload_ollama_model():
    """
    Ensures the Ollama model is unloaded by making a lightweight call with keep_alive="0s".
    This signals the Ollama server to unload the model based on its keep_alive mechanism.
    """
    global ollama_model_loaded
    logger.info(
        f"Ollama model '{model_name}' is currently loaded. Attempting to unload."
    )
    client = Client(host=ollama_base_url)
    try:
        logger.info(
            f"Sending unload signal for model '{model_name}' with keep_alive='0s'."
        )
        client.generate(
            model=model_name, prompt="", stream=False, options={"keep_alive": "0s"}
        )

        ollama_model_loaded = False
        logger.info(
            f"Ollama model '{model_name}' unload signal sent. Set ollama_model_loaded to False."
        )
    except Exception as e:
        logger.error(f"Error during Ollama model unload attempt: {e}")
        # We might still want to set ollama_model_loaded to False,
        # or handle the error more gracefully depending on desired behavior.
        # For now, let's assume the unload might have failed and keep the state.
        # Consider what should happen if the unload call itself fails.
        # Forcing ollama_model_loaded = False might be too optimistic.
        # However, the goal is to *attempt* unloading. If the attempt fails,
        # subsequent loads will try again.
        # Setting it to False reflects the *intent* to unload.
        ollama_model_loaded = False  # Tentatively set to False even on error, assuming server might still process it
        logger.warning(
            "Set ollama_model_loaded to False despite error, to allow future load attempts."
        )


if __name__ == "__main__":
    history = ""
    while True:
        question = input("\n\nYou\n--------\n")
        if history == "":
            answer = ask_Ollama(question)
            print("\nAssistant\n--------\n", end="")
            print(answer)

            if LOW_VRAM:
                unload_ollama_model()  # Example of how to use it
        else:
            answer = ask_Ollama(history + question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
            if LOW_VRAM:
                unload_ollama_model()
        history += f"User: {question}\nAssistant: {answer}\n"
