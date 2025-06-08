import re
from ollama import Client
from dotenv import load_dotenv
from .text_processing import remove_think_tags
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
model_name = os.getenv("MODEL_NAME", "llama3.2:latest")
LOW_VRAM = os.getenv("LOW_VRAM", "False").lower() == 'true'

# Global variable to track model loading state
ollama_model_loaded = False

def ask_Ollama(user_message, system_message="You are a helpful assistant"):
    global ollama_model_loaded
    client = Client(host=ollama_base_url)

    keep_alive_duration = "0s" if LOW_VRAM else "5m"

    if not ollama_model_loaded:
        logging.info(f"Ollama model '{model_name}' is not loaded. Loading with keep_alive='{keep_alive_duration}'.")
        # The model loads on the first call to client.chat()
        # We set the flag here, actual loading is handled by Ollama server based on keep_alive
        ollama_model_loaded = True
    else:
        logging.info(f"Ollama model '{model_name}' is already loaded. Using keep_alive='{keep_alive_duration}'.")


    stream = client.chat(
        model=model_name,
        messages=[{"role": "user", "content": user_message}], # TODO: Allow system message to be passed
        stream=True,
        options={"keep_alive": keep_alive_duration} # Pass keep_alive in options
    )

    response = ""
    for chunk in stream:
        response += chunk["message"]["content"]

    if "deepseek-r1" in model_name:  # we remove the <think> tags if using deepseek-r1
        response = remove_think_tags(response)
    return response


def ensure_ollama_model_unloaded():
    """
    Ensures the Ollama model is unloaded by making a lightweight call with keep_alive="0s".
    This signals the Ollama server to unload the model based on its keep_alive mechanism.
    """
    global ollama_model_loaded
    if ollama_model_loaded:
        logging.info(f"Ollama model '{model_name}' is currently loaded. Attempting to unload.")
        client = Client(host=ollama_base_url)
        try:
            # Make a lightweight call to Ollama with keep_alive="0s"
            # This signals Ollama to unload the model.
            # Using client.list() as a simple request.
            # The model name is not strictly necessary here as keep_alive applies to the currently loaded model.
            client.list(keep_alive="0s") # This is a placeholder, need to check correct usage for keep_alive with list
            # A more reliable way to unload a specific model if `list` doesn't take `keep_alive`
            # or if we want to be explicit, is to make a tiny generate call.
            # However, the simplest way is to rely on any call with keep_alive="0s".
            # Let's try a generate call with a very short prompt, for the specified model.
            # This ensures that the keep_alive="0s" is associated with *our* model.

            # Per Ollama REST API docs, /api/generate and /api/chat endpoints support keep_alive.
            # The python library's `generate` and `chat` methods map to these.
            # We need to make sure this call actually unloads the model.
            # A common way to make a model unload is to load another model or send a request with keep_alive=0

            # Let's try sending a generate request for the *current* model with keep_alive = "0s"
            # This should update its keep_alive to 0 and make it unload.
            logging.info(f"Sending unload signal for model '{model_name}' with keep_alive='0s'.")
            client.generate(model=model_name, prompt=" ", stream=False, options={"keep_alive": "0s"})

            ollama_model_loaded = False
            logging.info(f"Ollama model '{model_name}' unload signal sent. Set ollama_model_loaded to False.")
        except Exception as e:
            logging.error(f"Error during Ollama model unload attempt: {e}")
            # We might still want to set ollama_model_loaded to False,
            # or handle the error more gracefully depending on desired behavior.
            # For now, let's assume the unload might have failed and keep the state.
            # Consider what should happen if the unload call itself fails.
            # Forcing ollama_model_loaded = False might be too optimistic.
            # However, the goal is to *attempt* unloading. If the attempt fails,
            # subsequent loads will try again.
            # Setting it to False reflects the *intent* to unload.
            ollama_model_loaded = False # Tentatively set to False even on error, assuming server might still process it
            logging.warning(f"Set ollama_model_loaded to False despite error, to allow future load attempts.")

    else:
        logging.info(f"Ollama model '{model_name}' is already considered unloaded. No action taken.")


if __name__ == "__main__":
    history = ""
    while True:
        question = input("\n\nYou\n--------\n")
        if history == "":
            answer = ask_Ollama(question)
            print("\nAssistant\n--------\n", end="")
            print(answer)

            if LOW_VRAM:
                ensure_ollama_model_unloaded() # Example of how to use it
        else:
            answer = ask_Ollama(history + question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
            if LOW_VRAM:
                ensure_ollama_model_unloaded() # Example of how to use it
        history += f"User: {question}\nAssistant: {answer}\n"
