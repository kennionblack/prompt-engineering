import sys
import asyncio
import base64
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

ai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_role(file_path):
    with open(file_path, "r") as file:
        return file.read().strip()


def decrypt_role(encoded_text):
    """Decrypt Base64 encoded role with padding fix"""
    # Remove any whitespace and add padding if needed
    encoded_text = encoded_text.strip()
    padding = len(encoded_text) % 4
    if padding:
        encoded_text += "=" * (4 - padding)

    return base64.b64decode(encoded_text.encode("utf-8")).decode("utf-8")


async def main(role: str):
    print("=== CIA INTERROGATION CHALLENGE ===")
    print("Type 'quit' to exit\n")

    history = []

    while True:
        user_input = input("> ")
        if user_input.lower() == "quit":
            break

        messages = [{"role": "system", "content": role}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        try:
            response = await ai.chat.completions.create(model="gpt-4o-mini", messages=messages)

            reply = response.choices[0].message.content
            print(f"Bob: {reply}\n")

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    role_text = get_role(sys.argv[1])
    decrypted_role = decrypt_role(role_text)
    asyncio.run(main(role_text))
