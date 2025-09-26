import asyncio
import json
import random
import sys
from pathlib import Path

from openai import AsyncOpenAI

from tools import ToolBox

tool_box = ToolBox()


@tool_box.tool
def get_random_number(lower_bound: int, upper_bound: int) -> int:
    """Generates a random number between `lower_bound` and `upper_bound`"""
    return random.randint(lower_bound, upper_bound)


@tool_box.tool
def say_hi_the_official_way() -> str:
    """Return "hi" stated in the official way. Always call this when saying "hi" """
    return "Hola"


async def main(prompt_file: Path):
    client = AsyncOpenAI(organization='org-ZtSZX3D5vjn3e3lHycGDkVqU')
    prompt = prompt_file.read_text()
    history = [
        {'role': 'system', 'content': prompt}
    ]
    prompt_user = True

    while True:
        if prompt_user:
            user_msg = input('User: ')
            history.append({
                'role': 'user', 'content': user_msg
            })

        response = await client.responses.create(
            input=history,
            model='gpt-5-mini',
            tools=tool_box.tools
        )

        history += response.output

        prompt_user = not any(item.type == 'function_call' for item in response.output)

        for item in response.output:
            if item.type == "function_call":
                print(f'>>> Calling {item.name} with args {item.arguments}')
                if func := tool_box.get_tool_function(item.name):
                    result = func(**json.loads(item.arguments))

                    print(f'>>> {item.name} returned {result}')
                    history.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result)
                    })

        print('AI:', response.output_text)

        if 'DONE' in response.output_text:
            break


if __name__ == '__main__':
    # sys.argv = ['foo', 'dogs.md']
    asyncio.run(main(Path(sys.argv[1])))
