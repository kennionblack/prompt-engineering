import asyncio
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from config import Agent, load_config
from tools import ToolBox
from skill_manager import (
    create_skill_directory, 
    load_all_skill_functions, 
    add_skill_as_tool,
    create_skill_agent
)

from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
       old_text = "def old_function():\n    pass"
       new_text = "def new_function():\n    return 'updated'"

    2. INSERTING BEFORE existing text:
       old_text = "def main():"
       new_text = "def helper():\n    pass\n\ndef main():"

    3. INSERTING AFTER existing text:
       old_text = "import os"
       new_text = "import os\nimport sys"

    4. APPENDING to end of file:
       - First read the file to see its current ending
       - old_text = "# existing last line" (or whatever the actual last content is)
       - new_text = "# existing last line\n\n# new content"

    5. PREPENDING to start of file:
       - First read the file to see its current beginning
       - old_text = "#!/usr/bin/env python" (or whatever the actual first content is)
       - new_text = "# New header comment\n#!/usr/bin/env python"

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


# Skill management functions moved to skill_manager.py
# These are wrapper functions for backward compatibility

def create_skill_directory_wrapper(path: str, skill_name: str):
    """Wrapper for create_skill_directory from skill_manager."""
    return create_skill_directory(path, skill_name)


def add_skill_as_tool(skill_name: str):
    """
    Add a skill as a tool to the agents.yaml configuration file.

    This function modifies the existing agents.yaml file to include the new skill in the tools array.

    Args:
        path: Path to the directory containing agents.yaml (usually same as agent.py)
        skill_name: Name of the skill to add as a tool
    """
    import yaml

    try:
        # Note: we're assuming that agent.py and agents.yaml will always be in the same directory for the moment
        agents_yaml_path = Path(".") / "agents.yaml"

        if not agents_yaml_path.exists():
            return {
                "success": False,
                "message": f"agents.yaml not found at {agents_yaml_path}",
            }

        with open(agents_yaml_path, "r") as file:
            config = yaml.safe_load(file)

        if "agents" not in config:
            return {"success": False, "message": "No agents found in agents.yaml"}

        for agent in config["agents"]:
            if "tools" not in agent:
                agent["tools"] = []

            if skill_name not in agent["tools"]:
                agent["tools"].append(skill_name)

        with open(agents_yaml_path, "w") as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        # Now that we've written the new tools to the file, we need to make them known to the agent
        refresh_available_tools()

        return {
            "success": True,
            "message": f"Added skill '{skill_name}' to all agents in agents.yaml",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to add skill to agents.yaml: {str(e)}",
        }


def skill_function(func):
    """
    Decorator to mark functions in skill modules as exportable tools.
    
    Usage in skill main.py files:
    
    @skill_function
    def my_skill_function(param: str) -> str:
        '''Process data using this skill's specialized knowledge.'''
        return f"Processed: {param}"
    """
    func.is_skill_function = True
    return func


def load_skill_functions(skill_name: str, skills_path: str = "./agent/skills") -> dict:
    """
    Load and register functions from a specific skill directory.
    
    This implementation provides true lazy loading - only function signatures
    are loaded initially, with full skill context loaded on-demand when called.
    
    Args:
        skill_name: Name of the skill directory
        skills_path: Base path to skills directory
        
    Returns:
        Dictionary with success status and loaded functions info
    """
    import importlib.util
    import sys
    
    try:
        skill_dir = Path(skills_path) / skill_name
        
        if not skill_dir.exists():
            return {"success": False, "message": f"Skill directory not found: {skill_dir}"}
        
        # Look for main.py in the skill directory
        main_py = skill_dir / "main.py"
        if not main_py.exists():
            return {"success": False, "message": f"No main.py found in skill {skill_name}"}
        
        # Dynamically import the skill module
        module_name = f"skill_{skill_name}"
        spec = importlib.util.spec_from_file_location(module_name, main_py)
        
        if not spec or not spec.loader:
            return {"success": False, "message": f"Could not load module spec for {skill_name}"}
        
        # Remove existing module if it exists (for reloading)
        if module_name in sys.modules:
            del sys.modules[module_name]
            
        skill_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = skill_module
        spec.loader.exec_module(skill_module)
        
        # Find and register functions marked with @skill_function
        functions_registered = []
        
        for attr_name in dir(skill_module):
            attr = getattr(skill_module, attr_name)
            
            if (callable(attr) and 
                hasattr(attr, 'is_skill_function') and 
                not attr_name.startswith('_')):
                
                # Create a wrapper that provides skill context
                def create_skill_wrapper(skill_func, skill_dir_path, skill_name_ref):
                    def skill_wrapper(*args, **kwargs):
                        # This is where lazy loading happens - context loaded only when called
                        print(f"🔧 Executing skill function: {skill_func.__name__} from {skill_name_ref}")
                        
                        # Inject skill directory path into the function's context
                        if hasattr(skill_func, '__globals__'):
                            skill_func.__globals__['SKILL_DIR'] = skill_dir_path
                            skill_func.__globals__['SKILL_NAME'] = skill_name_ref
                        
                        return skill_func(*args, **kwargs)
                    
                    # Preserve function metadata for tool registration
                    skill_wrapper.__name__ = f"{skill_name}_{skill_func.__name__}"
                    skill_wrapper.__doc__ = skill_func.__doc__ or f"Skill function from {skill_name}"
                    skill_wrapper.__annotations__ = getattr(skill_func, '__annotations__', {})
                    
                    return skill_wrapper
                
                # Create the wrapper and register it as a tool
                wrapped_function = create_skill_wrapper(attr, skill_dir, skill_name)
                tool_box.tool(wrapped_function)
                
                functions_registered.append({
                    "name": wrapped_function.__name__,
                    "original_name": attr_name,
                    "doc": wrapped_function.__doc__
                })
        
        return {
            "success": True,
            "message": f"Loaded {len(functions_registered)} functions from skill {skill_name}",
            "functions": functions_registered
        }
        
    except Exception as e:
        return {"success": False, "message": f"Failed to load skill functions: {str(e)}"}


def load_all_skill_functions(skills_path: str = "./agent/skills") -> dict:
    """
    Scan the skills directory and load all skill functions as tools.
    
    This provides true lazy loading - only function signatures are loaded initially,
    with skill context loaded on-demand when functions are called.

    Args:
        skills_path: Path to the skills directory

    Returns:
        Dictionary with success status and list of loaded skill functions
    """
    try:
        skills_dir = Path(skills_path)
        if not skills_dir.exists():
            return {
                "success": False,
                "message": f"Skills directory not found: {skills_dir}",
            }

        loaded_skills = []
        total_functions = 0

        # Scan each subdirectory in the skills directory
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            # Load functions from this skill
            result = load_skill_functions(skill_dir.name, skills_path)
            if result["success"]:
                loaded_skills.append({
                    "name": skill_dir.name,
                    "functions": result.get("functions", [])
                })
                function_count = len(result.get("functions", []))
                total_functions += function_count
                print(f"Loaded {function_count} functions from skill: {skill_dir.name}")
            else:
                print(f"Failed to load skill {skill_dir.name}: {result['message']}")

        return {
            "success": True,
            "message": f"Loaded {total_functions} functions from {len(loaded_skills)} skills",
            "loaded_skills": loaded_skills,
            "total_functions": total_functions
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to load skill functions: {str(e)}",
        }


def refresh_available_tools(config_file_path: str = "./agents.yaml") -> dict:
    """
    Refresh available tools by reloading the agents.yaml configuration.

    This function reloads the YAML configuration and updates the global tool_box
    with any new tools that have been added to agents since the last load.

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
        skills_result = load_all_skill_functions("./agent/skills", tool_box)

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
    main_agent = config["main"]
    asyncio.run(run_agent(agents[main_agent], tool_box, None))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
