from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()
openai_base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
openai_api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("MODEL_NAME")


client = OpenAI(base_url=openai_base_url, api_key=openai_api_key)

def ask_LLM(user_message, system_message="You are a helpful assistant"):

    stream = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": user_message}],
        stream=True,
    )

    assistant_message = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            assistant_message += chunk.choices[0].delta.content
    return assistant_message

if __name__ == "__main__":
    history = ""
    while True:
        question = input("\n\nYou\n--------\n")
        if history == "":
            answer = ask_LLM(question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
        else:
            answer = ask_LLM(history + question)
            print("\nAssistant\n--------\n", end="")
            print(answer)
        history += f"User: {question}\nAssistant: {answer}\n"