from pathlib import Path
from config import Agent, load_config
from tools import ToolBox

_current_agents = {}
_config_file_path = Path("./agents.yaml")


def get_current_agents() -> dict:
    """Get the current agents registry"""
    return _current_agents


def set_config_file_path(path: Path):
    """Set the config file path for agent reloading"""
    global _config_file_path
    _config_file_path = path


def add_agent_tools(agents: dict[str, Agent], tool_box: ToolBox, run_agent_func):
    """
    Register agents as tools in the toolbox.

    Args:
        agents: Dictionary of agent configurations
        tool_box: ToolBox instance to register with
        run_agent_func: The run_agent function to use for delegation
    """
    for name, agent in agents.items():
        tool_box.add_agent_tool(agent, run_agent_func)


def reload_agents_from_config(tool_box: ToolBox, run_agent_func):
    """
    Reload agents from config file and re-register them with the toolbox.
    Called when skills are created/removed to pick up new skill agents.

    Args:
        tool_box: ToolBox instance to register with
        run_agent_func: The run_agent function to use for delegation
    """
    from skill_lifecycle import sync_skill_agents_to_all_tools

    # Sync skill agents to all tools lists
    sync_result = sync_skill_agents_to_all_tools(str(_config_file_path))
    if sync_result.get("updates"):
        print(f"Synced {len(sync_result['updates'])} skill agent(s) to tools lists")

    # Reload config
    config = load_config(_config_file_path)
    updated_agents = {agent["name"]: agent for agent in config["agents"]}

    # Re-register agents to pick up tool list changes
    for name, agent in updated_agents.items():
        tool_box.add_agent_tool(agent, run_agent_func)

    # Update global registry
    _current_agents.clear()
    _current_agents.update(updated_agents)

    print(f"Reloaded {len(updated_agents)} agent(s)")
