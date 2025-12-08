import asyncio
import json
import sys
import logging
import traceback
from pathlib import Path

from openai import AsyncOpenAI

from config import Agent, load_config
from tools import ToolBox
from s3_sync import S3SkillSync, sync_to_s3
from skill_execution import validate_python_code, validate_skill_code_with_wrapper
from result_chunker import chunk_large_result
from agent_registry import (
    get_current_agents,
    set_config_file_path,
    reload_agents_from_config as _reload_agents,
    add_agent_tools,
)
from skill_observer import register_skill_observers
from skill_lifecycle import sync_skill_agents_to_all_tools

from dotenv import load_dotenv
import os

load_dotenv()

# Suppress httpx info logs that managed to turn themselves on
logging.getLogger("httpx").setLevel(logging.WARNING)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _handle_session_end_cli():
    """Handle session end with S3 sync and deletion confirmation"""
    print("\nChecking for skill changes...")
    syncer = S3SkillSync()
    deleted_skills = syncer.get_deleted_skills()
    modified_skills = syncer.get_modified_skills()

    changes_found = False

    if deleted_skills:
        changes_found = True
        print("\nThe following skills exist in S3 but were deleted locally:")
        for skill in sorted(deleted_skills):
            print(f"  • {skill}")

    if modified_skills:
        changes_found = True
        print("\nThe following skills have been modified locally:")
        for skill in sorted(modified_skills.keys()):
            print(f"  • {skill}")
    if changes_found:
        if deleted_skills:
            response = (
                input("\nDo you want to delete removed skills from S3? (yes/no): ")
                .strip()
                .lower()
            )

            if response in ["yes", "y"]:
                print("\nDeleting skills from S3...")
                syncer.delete_skills_from_s3(list(deleted_skills))
            else:
                print("\nKeeping removed skills in S3")

        if modified_skills:
            print("\nUploading modified skills to S3...")

    print("\nSyncing all skills to S3...")
    sync_to_s3()
    print("\nSession ended successfully")


# Register skill system observers before creating ToolBox
register_skill_observers()

tool_box = ToolBox()


def reload_agents_from_config():
    """
    Reload agents from config file and re-register them with the toolbox.
    Called when skills are created/removed to pick up new skill agents.
    """
    _reload_agents(tool_box, run_agent)


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


def _validate_python_file(file_path: Path, content: str) -> dict:
    """
    Validate Python file content. Determines if it's a skill main.py and applies
    appropriate validation (with or without sandbox wrapper).

    Args:
        file_path: Path to the Python file
        content: Python code to validate

    Returns:
        Dictionary with 'success' bool, 'errors' list, and 'warnings' list
    """
    # Check if this is a skill main.py file
    is_skill_main = file_path.name == "main.py" and "skills" in file_path.parts

    if is_skill_main:
        # Extract skill name from path
        try:
            skills_idx = file_path.parts.index("skills")
            skill_name = (
                file_path.parts[skills_idx + 1]
                if skills_idx + 1 < len(file_path.parts)
                else "unknown"
            )
        except (ValueError, IndexError):
            skill_name = "unknown"

        # Validate with sandbox wrapper for skill files
        return validate_skill_code_with_wrapper(content, skill_name)
    else:
        # Standard validation for non-skill Python files
        return validate_python_code(content, str(file_path))


@tool_box.tool
def write_file(path: str, content: str) -> dict:
    """
    Write content to a file. For Python files, validates syntax before writing.

    Args:
        path: File path to write to
        content: Content to write

    Returns:
        Dictionary with success status and any validation warnings
    """
    file_path = Path(path).resolve()

    # Validate Python files before writing
    if file_path.suffix == ".py":
        validation = _validate_python_file(file_path, content)

        if not validation["success"]:
            error_msg = "\n".join(validation["errors"])
            return {
                "success": False,
                "error": f"Python validation failed:\n{error_msg}",
                "validation_errors": validation["errors"],
            }

        # Write the file
        file_path.write_text(content)

        # Return success with any warnings
        result = {
            "success": True,
            "message": f"File written successfully: {file_path.name}",
        }

        if validation["warnings"]:
            result["warnings"] = validation["warnings"]
            result["message"] += f" (with {len(validation['warnings'])} warnings)"

        return result
    else:
        # Non-Python files - write directly
        file_path.write_text(content)
        return {
            "success": True,
            "message": f"File written successfully: {file_path.name}",
        }


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
            ellipsis = "..." if len(old_text) > 50 else ""
            return {
                "success": False,
                "message": f"Target text not found in file: '{old_text[:50]}{ellipsis}'",
            }

        modified_content = content.replace(old_text, new_text, 1)

        # Validate Python files after modification
        if file_path.suffix == ".py":
            validation = _validate_python_file(file_path, modified_content)

            if not validation["success"]:
                error_msg = "\n".join(validation["errors"])
                return {
                    "success": False,
                    "message": f"Modification would create invalid Python code:\n{error_msg}",
                    "validation_errors": validation["errors"],
                }

            file_path.write_text(modified_content)

            result = {
                "success": True,
                "message": f"Successfully modified {file_path.name}",
            }

            if validation["warnings"]:
                result["warnings"] = validation["warnings"]
                result["message"] += f" (with {len(validation['warnings'])} warnings)"

            return result
        else:
            # If it's not a skill file, write directly without validation
            file_path.write_text(modified_content)
            return {"success": True, "message": f"Successfully modified {file_path.name}"}

    except Exception as e:
        return {"success": False, "message": f"Failed to modify file {path}: {str(e)}"}


async def run_agent(
    agent: Agent, tool_box: ToolBox, message: str | None, interactive: bool = True
):
    agent_name = agent["name"]
    _current_agents = get_current_agents()
    if agent_name in _current_agents:
        agent = _current_agents[agent_name]

    print("")
    print(f"---- RUNNING {agent['name']} ----")
    if message:
        print(message)
        print("----------------------------------")

    history = [{"role": "system", "content": agent["prompt"]}]

    if message is None:
        user_input = await tool_box.run_tool("talk_to_user", message="")
        history.append({"role": "user", "content": user_input})
    else:
        history.append({"role": "user", "content": message})

    while True:
        # Get fresh tools list on each iteration (picks up newly registered agents)
        tools = tool_box.get_tools(agent["tools"])

        # Debug: print tool count
        # if len(tools) > 20:
        #     print(
        #         f"Agent {agent['name']} has {len(tools)} tools (expected ~{len(agent['tools'])})"
        #     )

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
                    chunked_result = chunk_large_result(result)

                    history.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(chunked_result),
                        }
                    )
                except TaskCompleteException as e:
                    return e.message

            elif item.type == "message":
                if isinstance(item.content, list) and len(item.content) > 0:
                    message_text = item.content[0].text
                else:
                    message_text = str(item.content)

                # Check if this agent is allowed to talk to user
                agent_tools = agent.get("tools", [])
                if "talk_to_user" in agent_tools:
                    user_input = await tool_box.run_tool(
                        "talk_to_user", message=message_text
                    )
                    history.append({"role": "user", "content": user_input})
                else:
                    # Delegated agent trying to communicate - this is an error
                    # Return the message as the agent's final output
                    # print(f"Delegated agent '{agent['name']}' attempted to send message {message_text[:100]}")
                    return message_text

            elif item.type == "reasoning":
                print(f"---- {agent['name']} REASONED ----")

            else:
                print(item, file=sys.stderr)


async def main(config_file: Path):
    set_config_file_path(config_file)

    # Sync all tools to ensure that they are available
    sync_result = sync_skill_agents_to_all_tools(str(config_file))
    if sync_result.get("updates"):
        print(f"Synced skill agents: {len(sync_result['updates'])} updates made")

    config = load_config(config_file)
    agents = {agent["name"]: agent for agent in config["agents"]}
    add_agent_tools(agents, tool_box, run_agent)

    # Skills are auto-loaded by the observer pattern in skill_manager
    # After skills load, agents.yaml may have been updated with new skill agents
    # Reload config and re-register agents to pick up tool list changes
    updated_config = load_config(config_file)
    updated_agents = {agent["name"]: agent for agent in updated_config["agents"]}

    # Re-register all agents as existing agents may have new tools added
    # This ensures agent tool lists are current
    for name, agent in updated_agents.items():
        tool_box.add_agent_tool(agent, run_agent)

    agents = updated_agents
    _current_agents = get_current_agents()
    _current_agents.update(agents)

    main_agent = config["main"]
    await run_agent(agents[main_agent], tool_box, None, interactive=True)


if __name__ == "__main__":
    if "--web" in sys.argv:
        # web_interface imported here to avoid circular dependency
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
            _handle_session_end_cli()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
