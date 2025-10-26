import asyncio
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from config import Agent, load_config
from tools import ToolBox

from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import skill_manager BEFORE creating tool_box so observer can be registered first
import skill_manager

# Now create the toolbox - this will trigger the observer
tool_box = ToolBox()


@tool_box.tool
def talk_to_user(message: str) -> str:
    """Send a message to the user and get the user's response.

    This is the ONLY way to communicate with the user,
    so all information to and from the user will come through this function.
    """
    print()
    print("AI: ", message)
    return input("User: ")


@tool_box.tool
def talk_to_named_user(name: str, message: str) -> str:
    """Send a message to the specified user and get the user's response.

    This is the ONLY way to communicate with a user,
    so all information to and from a user will come through this function.
    """
    print()
    print(f"AI (to {name}): ", message)
    return input(f"{name}: ")


@tool_box.tool
def plan(thoughts: str):
    """
    Plan out what you want to do over the next few interactions with the user.

    Write your thoughts and strategy here.

    For example, if you need to ask the user a series of questions,
    you can enumerate them here to make sure you cover them all.

    Or if you need to call a series of functions, list them here
    so you remember what you planned to do.
    """
    print()
    print("----- PLAN ------")
    print(thoughts)
    print("-----------------")


@tool_box.tool
def reason(thoughts: str):
    """
    Reason about the task at hand.

    Write your thoughts here.
    You can also record information here you need to keep track of,
    but don't need to send to the user.

    IMPORTANT: This information is NOT visible to the user.
    If you need to send information to the user, use a different function.
    """
    print()
    print("--- REASONING ---")
    print(thoughts)
    print("-----------------")
    return None


@tool_box.tool
def make_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


@tool_box.tool
def write_file(path: str, content: str):
    Path(path).resolve().write_text(content)


@tool_box.tool
def read_file(path: str) -> str:
    return Path(path).resolve().absolute().read_text()


@tool_box.tool
def modify_file(path: str, old_text: str, new_text: str) -> dict:
    """
    Modify a file by finding and replacing text. This is a simple but powerful approach
    that can accomplish insert, append, prepend, and replace operations through strategic
    find/replace operations.

    Args:
        path: Path to the file to modify
        old_text: Exact text to find and replace (must match exactly including whitespace)
        new_text: Text to replace old_text with

    IMPORTANT USAGE PATTERNS FOR AGENTS:

    1. REPLACING TEXT:
       old_text = "def old_function():\\n    pass"
       new_text = "def new_function():\\n    return 'updated'"

    2. INSERTING BEFORE existing text:
       old_text = "def main():"
       new_text = "def helper():\\n    pass\\n\\ndef main():"

    3. INSERTING AFTER existing text:
       old_text = "import os"
       new_text = "import os\\nimport sys"

    4. APPENDING to end of file:
       - First read the file to see its current ending
       - old_text = "# existing last line" (or whatever the actual last content is)
       - new_text = "# existing last line\\n\\n# new content"

    5. PREPENDING to start of file:
       - First read the file to see its current beginning
       - old_text = "#!/usr/bin/env python" (or whatever the actual first content is)
       - new_text = "# New header comment\\n#!/usr/bin/env python"

    CRITICAL SUCCESS TIPS:
    - Always read the file first to see the exact text you want to target
    - Include enough context to make your old_text unique
    - Match whitespace, indentation, and newlines exactly
    - For multi-line changes, include surrounding lines for context
    - Test with a small, unique target first if unsure and undo if necessary

    Returns:
        Dictionary with success status and explanatory message
    """
    try:
        file_path = Path(path).resolve()

        if file_path.exists():
            content = file_path.read_text()
        else:
            content = ""

        if old_text not in content:
            return {
                "success": False,
                "message": f"Target text not found in file: '{old_text[:50]}{'...' if len(old_text) > 50 else ''}'",
            }

        modified_content = content.replace(old_text, new_text, 1)

        file_path.write_text(modified_content)

        return {"success": True, "message": f"Successfully modified {file_path.name}"}

    except Exception as e:
        return {"success": False, "message": f"Failed to modify file {path}: {str(e)}"}


def create_empty_file(path: str, file_name: str):
    """Create an empty file at the specified path with the given filename."""
    file_path = Path(path) / file_name

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.touch()

    return str(file_path.resolve())


def refresh_available_tools(config_file_path: str = "./agents.yaml") -> dict:
    """
    Refresh available tools by reloading the agents.yaml configuration and skill functions.

    This function:
    1. Reloads the YAML configuration for agents
    2. Loads skill functions from skill directories with true lazy loading
    3. Persists any new agents to the YAML file

    Args:
        config_file_path: Path to the agents.yaml file (defaults to current directory)

    Returns:
        Dictionary with success status and information about refreshed tools
    """
    try:
        config_path = Path(config_file_path)

        if not config_path.exists():
            return {
                "success": False,
                "message": f"Configuration file not found: {config_path}",
            }

        config = load_config(config_path)

        if "agents" not in config:
            return {"success": False, "message": "No agents found in configuration file"}

        # Get current tool count for comparison
        initial_tool_count = len(tool_box._tools)

        # Reload agents from YAML config
        agents = {agent["name"]: agent for agent in config["agents"]}
        add_agent_tools(agents, tool_box)

        # Load all skill functions as tools (true lazy loading)
        skills_result = skill_manager.load_all_skill_functions("./agent/skills", tool_box)

        # Calculate how many tools were added
        final_tool_count = len(tool_box._tools)
        tools_added = final_tool_count - initial_tool_count

        return {
            "success": True,
            "message": f"Refreshed tools from {config_path.name}. Added {tools_added} new tools. {skills_result.get('message', '')}",
            "total_tools": final_tool_count,
            "tools_added": tools_added,
            "skill_functions_loaded": skills_result.get("total_functions", 0),
            "skills_loaded": skills_result.get("loaded_skills", []),
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to refresh tools: {str(e)}"}


def add_agent_tools(agents: dict[str, Agent], tool_box: ToolBox):
    for name, agent in agents.items():
        tool_box.add_agent_tool(agent, run_agent)


async def run_agent(agent: Agent, tool_box: ToolBox, message: str | None):
    print("")
    print(f"---- RUNNING {agent['name']} ----")
    if message:
        print(message)
        print("----------------------------------")

    history = [{"role": "system", "content": agent["prompt"]}]
    if message is not None:
        history.append({"role": "user", "content": message})

    tools = tool_box.get_tools(agent["tools"])

    while True:
        response = await client.responses.create(
            input=history, model="gpt-5-mini", tools=tools, **agent.get("kwargs", {})
        )

        history += response.output

        for item in response.output:
            if item.type == "function_call":
                print(f"---- {agent['name']} calling {item.name} ----")
                result = await tool_box.run_tool(item.name, **json.loads(item.arguments))

                history.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

            elif item.type == "message":
                return response.output_text

            elif item.type == "reasoning":
                print(f"---- {agent['name']} REASONED ----")

            else:
                print(item, file=sys.stderr)


def main(config_file: Path):
    config = load_config(config_file)
    agents = {agent["name"]: agent for agent in config["agents"]}
    add_agent_tools(agents, tool_box)

    # Load skill functions on startup
    skill_manager.load_all_skill_functions("./agent/skills", tool_box)

    main_agent = config["main"]
    asyncio.run(run_agent(agents[main_agent], tool_box, None))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
