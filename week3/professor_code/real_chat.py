import asyncio
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from tools import ToolBox

tool_box = ToolBox()


@tool_box.tool
def run_python_code(code: str) -> str:
    """
        Executes the provided `code` in a python `exec` block.
        Returns the STDOUT from running the code
        """
    # Execute code and capture stdout/stderr output. If an exception occurs,
    # include the traceback in the returned output so callers can see the error.
    import io
    import contextlib
    import traceback

    buffer = io.StringIO()
    globals_dict = {"__name__": "__main__"}
    locals_dict = {}

    try:
        with contextlib.redirect_stdout(buffer):
            # run the code in a fresh globals/locals mapping
            exec(code, globals_dict, locals_dict)
    except Exception:
        # write traceback to the buffer so the caller sees the error
        traceback.print_exc(file=buffer)

    return buffer.getvalue()


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
