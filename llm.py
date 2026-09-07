import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing from .env"
    )

client = Groq(
    api_key=GROQ_API_KEY
)


def ask_groq(messages: list) -> str:

    clean_messages = []

    for message in messages:
        clean_messages.append(
            {
                "role": str(message["role"]),
                "content": str(message["content"])
            }
        )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=clean_messages
    )

    return response.choices[0].message.content