from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
openai_base_url = os.getenv("OPENAI_BASE_URL", "http://10.161.141.2:1234/v1")
openai_api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("MODEL_NAME")

client = ChatOpenAI(
    base_url=openai_base_url,
    api_key=openai_api_key,
    model=model_name,
    streaming=True
)


def ask_LLM(user_message, system_message="You are a helpful assistant"):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    assistant_message = ""
    for chunk in client.stream(input=messages, stream=True):
        if hasattr(chunk, "content"):
            assistant_message += chunk.content

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
