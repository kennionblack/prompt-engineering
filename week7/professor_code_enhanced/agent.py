import asyncio
import json
import sys
import logging
from pathlib import Path

from openai import AsyncOpenAI

from config import Agent, load_config
from tools import ToolBox

from dotenv import load_dotenv
import os

load_dotenv()

# Suppress httpx info logs that managed to turn themselves on
logging.getLogger("httpx").setLevel(logging.WARNING)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global agents registry for runtime reloading
_current_agents = {}
_config_file_path = Path("./agents.yaml")

# Register skill system observers before creating ToolBox
from skill_observer import register_skill_observers

register_skill_observers()

# Now create the toolbox - observers will auto-load skills
tool_box = ToolBox()


def reload_agents_from_config():
    """
    Reload agents from config file and re-register them with the toolbox.
    Called when skills are created/removed to pick up new skill agents.
    """
    from skill_lifecycle import sync_skill_agents_to_all_tools

    # Sync skill agents to all tools lists
    sync_result = sync_skill_agents_to_all_tools(str(_config_file_path))
    if sync_result.get("updates"):
        print(f"🔄 Synced {len(sync_result['updates'])} skill agent(s) to tools lists")

    # Reload config
    config = load_config(_config_file_path)
    updated_agents = {agent["name"]: agent for agent in config["agents"]}

    # Re-register ALL agents to pick up tool list changes
    for name, agent in updated_agents.items():
        tool_box.add_agent_tool(agent, run_agent)

    # Update global registry
    _current_agents.clear()
    _current_agents.update(updated_agents)

    print(f"✅ Reloaded {len(updated_agents)} agent(s)")


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

    This is the ONLY way to communicate with the user,
    so all information to and from the user will come through this function.
    """
    print()
    print(f"AI to {name}: ", message)
    return input(f"{name}: ")


class TaskCompleteException(Exception):
    """Exception to signal task completion and return control to calling agent"""

    def __init__(self, message: str = "Task completed"):
        self.message = message
        super().__init__(self.message)


@tool_box.tool
def complete_delegated_task(summary: str) -> str:
    """Complete a delegated task and return control to the calling agent.

    Use this when you have been called by another agent (like user_interface calling skill_builder)
    and you have finished the requested task. This will end the current agent's execution
    and return control to the calling agent.

    Args:
        summary: A brief summary of what was accomplished

    Returns:
        The summary message
    """
    print(f"\n✅ Task completed: {summary}")
    raise TaskCompleteException(summary)


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


def add_agent_tools(agents: dict[str, Agent], tool_box: ToolBox):
    for name, agent in agents.items():
        tool_box.add_agent_tool(agent, run_agent)


async def run_agent(
    agent: Agent, tool_box: ToolBox, message: str | None, interactive: bool = True
):
    # Always use the current agent config to pick up runtime updates
    agent_name = agent["name"]
    if agent_name in _current_agents:
        agent = _current_agents[agent_name]

    print("")
    print(f"---- RUNNING {agent['name']} ----")
    if message:
        print(message)
        print("----------------------------------")

    history = [{"role": "system", "content": agent["prompt"]}]

    # Use GPT-4o for initial greeting with skills context
    if message is None and agent["name"] == "user_interface":
        try:
            skills_result = await tool_box.run_tool("list_skills")
            skills_context = f"\n\nAvailable skills: {skills_result.get('message', '')}"
        except:
            skills_context = ""

        greeting_response = await client.responses.create(
            input=[{"role": "system", "content": agent["prompt"] + skills_context}],
            model="gpt-4o",
            tools=[],
            temperature=0.3,
        )

        for item in greeting_response.output:
            if item.type == "message":
                greeting_text = (
                    item.content[0].text
                    if isinstance(item.content, list)
                    else str(item.content)
                )
                # Use talk_to_user tool to send greeting and get response
                user_input = await tool_box.run_tool(
                    "talk_to_user", message=greeting_text
                )
                break

        history.append({"role": "user", "content": user_input})

    elif message is not None:
        history.append({"role": "user", "content": message})

    while True:
        # Get fresh tools list on each iteration (picks up newly registered agents)
        tools = tool_box.get_tools(agent["tools"])

        # Debug: print tool count
        if len(tools) > 20:
            print(
                f"⚠️  Agent {agent['name']} has {len(tools)} tools (expected ~{len(agent['tools'])})"
            )

        response = await client.responses.create(
            input=history, model="gpt-5-mini", tools=tools, **agent.get("kwargs", {})
        )

        history += response.output
        for item in response.output:
            if item.type == "function_call":
                print(f"---- {agent['name']} calling {item.name} ----")
                try:
                    result = await tool_box.run_tool(
                        item.name, **json.loads(item.arguments)
                    )

                    # Apply chunking to large results before adding to history
                    from result_chunker import chunk_large_result

                    chunked_result = chunk_large_result(result)

                    history.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(chunked_result),
                        }
                    )
                except TaskCompleteException as e:
                    # Task is complete, return the summary message
                    return e.message

            elif item.type == "message":
                # Extract the text from the ResponseOutputText object in the list
                if isinstance(item.content, list) and len(item.content) > 0:
                    message_text = item.content[0].text
                else:
                    message_text = str(item.content)

                # Always use talk_to_user tool for communication
                # This allows web interface to override it
                user_input = await tool_box.run_tool("talk_to_user", message=message_text)
                history.append({"role": "user", "content": user_input})

            elif item.type == "reasoning":
                print(f"---- {agent['name']} REASONED ----")

            else:
                print(item, file=sys.stderr)


async def main(config_file: Path):
    global _config_file_path, _current_agents
    _config_file_path = config_file

    # First, sync all skill agents to ensure they're in all agents' tools lists
    # This is a repair operation for agents created before auto-add logic
    from skill_lifecycle import sync_skill_agents_to_all_tools

    sync_result = sync_skill_agents_to_all_tools(str(config_file))
    if sync_result.get("updates"):
        print(f"Synced skill agents: {len(sync_result['updates'])} updates made")

    config = load_config(config_file)
    agents = {agent["name"]: agent for agent in config["agents"]}
    add_agent_tools(agents, tool_box)

    # Skills are auto-loaded by the observer pattern in skill_manager
    # After skills load, agents.yaml may have been updated with new skill agents
    # Reload config and re-register ALL agents to pick up tool list changes
    updated_config = load_config(config_file)
    updated_agents = {agent["name"]: agent for agent in updated_config["agents"]}

    # Re-register ALL agents (existing agents may have new tools added)
    # This ensures agent tool lists are current
    for name, agent in updated_agents.items():
        if name not in agents:
            # New agent - register it
            tool_box.add_agent_tool(agent, run_agent)
        else:
            # Existing agent - update its registration to pick up new tools
            # The agent may have had skill agents added to its tools list
            tool_box.add_agent_tool(agent, run_agent)

    agents = updated_agents  # Use the updated agents dict
    _current_agents.update(agents)  # Update global registry

    main_agent = config["main"]
    await run_agent(agents[main_agent], tool_box, None, interactive=True)


if __name__ == "__main__":
    # Check for web mode flag
    if "--web" in sys.argv:
        from web_interface import main as web_main

        web_main()
    else:
        # CLI mode
        try:
            if len(sys.argv) == 1:
                asyncio.run(main(Path("./agents.yaml")))
            else:
                config_file = sys.argv[1] if sys.argv[1] != "--web" else "./agents.yaml"
                asyncio.run(main(Path(config_file)))
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
