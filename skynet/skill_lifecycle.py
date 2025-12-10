import shutil
import yaml
from pathlib import Path
from typing import Dict, Any

from skill_templates import get_readme_template, get_main_py_template
from tools import notify_tool_change
from dependency_manager import (
    check_skill_dependencies,
    install_skill_dependencies,
    get_dependency_info,
)


def sync_skill_agents_to_all_tools(
    agents_yaml_file: str = "./agents.yaml",
) -> Dict[str, Any]:
    """
    Ensure all skill agents (ending in _agent) are added to all other agents' tools lists.
    This is a repair function to fix agents that were created before the auto-add logic.

    Args:
        agents_yaml_file: Path to agents.yaml

    Returns:
        Dictionary with success status and list of updates made
    """
    agents_yaml_path = Path(agents_yaml_file)
    if not agents_yaml_path.exists():
        return {"success": False, "message": "agents.yaml not found"}

    with open(agents_yaml_path, "r") as file:
        config = yaml.safe_load(file) or {}

    if "agents" not in config:
        return {"success": False, "message": "No agents found in config"}

    # Find all skill agents (agents whose names end with _agent)
    skill_agents = [
        agent["name"]
        for agent in config["agents"]
        if agent.get("name", "").endswith("_agent")
    ]

    updates = []

    # Add each skill agent to all other agents' tools
    for agent in config["agents"]:
        agent_name = agent.get("name")
        if "tools" not in agent:
            agent["tools"] = []

        for skill_agent_name in skill_agents:
            # Don't add skill agents to themselves
            if agent_name != skill_agent_name:
                if skill_agent_name not in agent["tools"]:
                    agent["tools"].append(skill_agent_name)
                    updates.append(f"Added {skill_agent_name} to {agent_name}")

    # Write the updated config
    with open(agents_yaml_path, "w") as file:
        yaml.dump(config, file, default_flow_style=False, sort_keys=False)

    return {
        "success": True,
        "message": f"Synced {len(skill_agents)} skill agents to all other agents",
        "skill_agents": skill_agents,
        "updates": updates,
    }


def create_skill_directory(path: str, skill_name: str) -> Dict[str, Any]:
    """
    Create a skill directory structure with templates.

    Args:
        path: Base path for skills (default is ./agent/skills)
        skill_name: Name of the new skill

    Returns:
        Dictionary with success status and created path
    """
    base_path = Path(path).resolve()

    if str(base_path).endswith("agent/skills"):  # current path is exactly agent/skills
        skill_directory_path = base_path / skill_name
    elif "agent/skills" in str(base_path):  # current path is nested in agent/skills
        path_parts = base_path.parts
        agent_skills_index = None
        for i, part in enumerate(path_parts):
            if part == "skills" and i > 0 and path_parts[i - 1] == "agent":
                agent_skills_index = i
                break

        if agent_skills_index is not None:
            base_parts = path_parts[: agent_skills_index + 1]
            skills_base = Path(*base_parts)
            skill_directory_path = skills_base / skill_name
        else:  # this shouldn't happen but just in case
            skill_directory_path = base_path / "agent" / "skills" / skill_name
    else:  # agent/skills directory does not exist in path
        skill_directory_path = base_path / "agent" / "skills" / skill_name

    # Validate skill name
    if not skill_name or not skill_name.replace("_", "").replace("-", "").isalnum():
        return {
            "success": False,
            "message": f"Invalid skill name '{skill_name}'. Use only letters, numbers, underscores, and hyphens.",
        }

    if skill_directory_path.exists():
        return {
            "success": False,
            "message": f"Skill '{skill_name}' already exists at {skill_directory_path}",
        }

    try:
        print(f"Creating skill '{skill_name}' at {skill_directory_path}")

        skill_directory_path.mkdir(parents=True, exist_ok=True)
        scripts_dir = skill_directory_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Write template files
        readme_content = get_readme_template(skill_name)
        main_py_content = get_main_py_template(skill_name)

        (skill_directory_path / "README.md").write_text(readme_content)
        (skill_directory_path / "main.py").write_text(main_py_content)

        # Create empty requirements.txt
        requirements_file = skill_directory_path / "requirements.txt"
        if not requirements_file.exists():
            requirements_file.write_text(
                "# Add Python package dependencies here, one per line\n# Example:\n# requests>=2.31.0\n# beautifulsoup4>=4.12.0\n"
            )

        # Automatically create the skill agent for this skill
        agent_result = create_skill_agent(
            skill_name, f"Agent for {skill_name} skill functionality", "./agents.yaml"
        )

        # Notify all toolboxes that a new skill was created
        notify_tool_change(
            "skill_created",
            {
                "skill_name": skill_name,
                "path": str(skill_directory_path),
                "message": f"New skill '{skill_name}' created with agent",
            },
        )

        return {
            "success": True,
            "message": f"Created skill directory structure and agent for {skill_name}",
            "path": str(skill_directory_path),
            "agent_created": agent_result.get("success", False),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create skill directory for skill {skill_name}: {str(e)}",
        }


def update_agents_yaml_with_skills(
    skill_function_map: dict, agents_yaml_path: str = "./agents.yaml"
) -> Dict[str, Any]:
    """
    Update agents.yaml to include skill functions in agent tool lists.

    Args:
        skill_function_map: Dictionary mapping skill_name -> [function_names]
        agents_yaml_path: Path to agents.yaml file

    Returns:
        Dictionary with success status and modified agents list
    """
    try:
        agents_yaml_file = Path(agents_yaml_path)
        if not agents_yaml_file.exists():
            return {
                "success": False,
                "message": f"agents.yaml not found at {agents_yaml_path}",
            }

        with open(agents_yaml_file, "r") as file:
            config = yaml.safe_load(file) or {}

        if "agents" not in config:
            return {"success": False, "message": "No agents section found in agents.yaml"}

        modified_agents = []

        for agent in config["agents"]:
            agent_name = agent.get("name", "unknown")
            current_tools = agent.get("tools", [])

            # Remove any existing skill functions from the tool list in case skill was reloaded
            cleaned_tools = []
            for tool in current_tools:
                # Keep agent tools (they end with _agent)
                if tool.endswith("_agent"):
                    cleaned_tools.append(tool)
                    continue

                # Remove bare skill names (they're redundant with skill agents)
                if tool in skill_function_map.keys():
                    continue

                # Ignore skill function tools (they contain skill_name_ but aren't agents)
                is_skill_function = any(
                    f"{skill_name}_" in tool for skill_name in skill_function_map.keys()
                )
                if not is_skill_function:
                    cleaned_tools.append(tool)

            skill_functions_to_add = []

            if agent_name.endswith("_agent"):
                # Extract skill name from agent name
                potential_skill = agent_name.replace("_agent", "")

                # Add only functions from this specific skill
                if potential_skill in skill_function_map:
                    skill_functions_to_add = skill_function_map[potential_skill]
            # else:
            #     # For non-skill agents, add all skill functions
            #     for skill_name, function_names in skill_function_map.items():
            #         skill_functions_to_add.extend(function_names)

            updated_tools = cleaned_tools + skill_functions_to_add

            if set(current_tools) != set(updated_tools):
                agent["tools"] = updated_tools
                modified_agents.append(agent_name)

        # Write back to file if any changes were made
        if modified_agents:
            with open(agents_yaml_file, "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)

            # Collect all unique skill functions that were added
            all_skill_functions = []
            for function_names in skill_function_map.values():
                all_skill_functions.extend(function_names)

            return {
                "success": True,
                "message": f"Updated agents.yaml with targeted skill functions for agents: {', '.join(modified_agents)}",
                "modified_agents": modified_agents,
                "skill_functions_added": all_skill_functions,
            }
        else:
            all_skill_functions = []
            for function_names in skill_function_map.values():
                all_skill_functions.extend(function_names)

            return {
                "success": True,
                "message": "No changes needed - agents.yaml already up to date",
                "skill_functions": all_skill_functions,
            }

    except Exception as e:
        return {"success": False, "message": f"Failed to update agents.yaml: {str(e)}"}


def add_skill_as_tool(
    agents_yaml_path: str, skill_name: str, skill_description: str
) -> Dict[str, Any]:
    """
    Add a skill as a tool to the agents.yaml configuration file.

    Args:
        agents_yaml_path: Path to the agents.yaml file
        skill_name: Name of the skill to add as a tool
        skill_description: Description of what the skill does

    Returns:
        Dictionary with success status and explanatory message
    """
    try:
        agents_yaml_file = Path(agents_yaml_path)

        if not agents_yaml_file.exists():
            return {
                "success": False,
                "message": f"agents.yaml not found at {agents_yaml_file}",
            }

        with open(agents_yaml_file, "r") as file:
            config = yaml.safe_load(file)

        if "agents" not in config:
            return {"success": False, "message": "No agents found in configuration"}

        skills_added = 0
        for agent in config["agents"]:
            if "tools" not in agent:
                agent["tools"] = []

            # Add skill if not already in tools list
            if skill_name not in agent["tools"]:
                agent["tools"].append(skill_name)
                skills_added += 1

        with open(agents_yaml_file, "w") as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"Added skill '{skill_name}' to {skills_added} agent(s) and persisted to {agents_yaml_file.name}",
        }

    except ImportError:
        return {
            "success": False,
            "message": "PyYAML is required to modify YAML files. Install with: pip install pyyaml",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to add skill to agents.yaml: {str(e)}",
        }


def create_skill_agent(
    skill_name: str, skill_description: str, agents_yaml_path: str
) -> Dict[str, Any]:
    """
    Create a new skill agent and persist it to the agents.yaml file.

    This creates a dedicated agent for the skill that can be called by other agents,
    providing a way to encapsulate skill functionality as a callable agent.

    Args:
        skill_name: Name of the skill
        skill_description: Description of the skill
        agents_yaml_path: Path to the agents.yaml file

    Returns:
        Dictionary with success status and agent configuration
    """
    try:
        agents_yaml_file = Path(agents_yaml_path)

        # Create agent configuration
        skill_agent = {
            "name": f"{skill_name}_agent",
            "description": skill_description,
            "model": "gpt-4o",
            "prompt": f"""You are the {skill_name} skill agent.

              Your purpose is to execute the {skill_name} skill functionality.

              You have access to specialized functions from the {skill_name} skill that will be loaded
              dynamically when you need them. Use these functions to accomplish the requested tasks.

              Focus on using the skill-specific functions available to you rather than general tools
              when possible, as they contain specialized knowledge for this domain.
              """,
            "tools": ["read_file", "write_file", "modify_file", "reason"],
            # "kwargs": {"max_tokens": 4000},
        }

        if agents_yaml_file.exists():
            with open(agents_yaml_file, "r") as file:
                config = yaml.safe_load(file) or {}
        else:
            config = {"agents": [], "main": "user_interface"}

        if "agents" not in config:
            config["agents"] = []

        existing_agent = None
        for i, agent in enumerate(config["agents"]):
            if agent.get("name") == skill_agent["name"]:
                existing_agent = i
                break

        # Add or update the agent
        if existing_agent is not None:
            # Preserve existing tools when updating
            existing_tools = config["agents"][existing_agent].get("tools", [])
            skill_agent["tools"] = existing_tools  # Keep existing tools
            config["agents"][existing_agent] = skill_agent
            action = "Updated"
        else:
            config["agents"].append(skill_agent)
            action = "Added"

        with open(agents_yaml_file, "w") as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        # Add the skill agent as a tool to ALL agents so they can all leverage skills
        # This enables flexible agent collaboration without routing through user_interface
        agent_name = skill_agent["name"]
        agents_updated = []

        for agent in config["agents"]:
            # Don't add skill agents to themselves
            if agent.get("name") != agent_name:
                if "tools" not in agent:
                    agent["tools"] = []
                if agent_name not in agent["tools"]:
                    agent["tools"].append(agent_name)
                    agents_updated.append(agent.get("name"))

        # Write again with the updated tools
        with open(agents_yaml_file, "w") as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"{action} skill agent '{skill_agent['name']}' and made it available to all agents: {', '.join(agents_updated)}",
            "agent_config": skill_agent,
            "agents_updated": agents_updated,
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to create skill agent: {str(e)}"}


def check_skill_changes(skills_path: str = "./agent/skills") -> Dict[str, Any]:
    """
    Check for changes in the skills directory without reloading.

    Args:
        skills_path: Path to the skills directory

    Returns:
        Dictionary with change detection results
    """
    # Import here to avoid circular dependency
    from skill_loader import _loaded_skills

    try:
        skills_dir = Path(skills_path)
        if not skills_dir.exists():
            return {
                "success": False,
                "message": f"Skills directory not found: {skills_dir}",
            }

        # Get current skill directories
        current_skills = set()
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                current_skills.add(skill_dir.name)

        # Compare with previously loaded skills
        new_skills = current_skills - _loaded_skills
        removed_skills = _loaded_skills - current_skills

        return {
            "success": True,
            "has_changes": bool(new_skills or removed_skills),
            "new_skills": list(new_skills),
            "removed_skills": list(removed_skills),
            "current_skills": list(current_skills),
            "previously_loaded": list(_loaded_skills),
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to check skill changes: {str(e)}"}


def remove_skill_from_agents_yaml(
    skill_name: str, agents_yaml_file: str = "./agents.yaml"
) -> Dict[str, Any]:
    """
    Remove all references to a skill from the agents.yaml file.

    This removes:
    1. The skill name from any agent's tools list
    2. Any dedicated skill agent that matches the skill name

    Args:
        skill_name: Name of the skill to remove references for
        agents_yaml_file: Path to the agents.yaml file

    Returns:
        Dictionary with success status and details of what was removed
    """
    try:
        yaml_path = Path(agents_yaml_file)
        if not yaml_path.exists():
            return {
                "success": True,
                "message": f"No agents.yaml file found at {yaml_path}",
                "changes_made": [],
            }

        with open(yaml_path, "r") as file:
            config = yaml.safe_load(file) or {}

        if "agents" not in config:
            return {
                "success": True,
                "message": "No agents found in configuration",
                "changes_made": [],
            }

        changes_made = []
        agents_to_remove = []

        # Process each agent
        for i, agent in enumerate(config["agents"]):
            agent_name = agent.get("name", f"agent_{i}")

            # Check for skill agent with {skill_name}_agent name
            if agent_name == f"{skill_name}_agent":
                agents_to_remove.append(i)
                changes_made.append(f"Removed skill agent '{agent_name}'")
                continue

            # Remove skill from tools list where present
            if "tools" in agent and isinstance(agent["tools"], list):
                original_tools = agent["tools"][:]
                # Remove exact skill name matches
                agent["tools"] = [tool for tool in agent["tools"] if tool != skill_name]
                # Also remove any tools that start with skill_name_ (skill functions)
                # if there's skill name overlap this could get hairy but for now I'm fine with this
                agent["tools"] = [
                    tool
                    for tool in agent["tools"]
                    if not tool.startswith(f"{skill_name}_")
                ]

                removed_tools = set(original_tools) - set(agent["tools"])
                if removed_tools:
                    changes_made.append(
                        f"Removed tools {list(removed_tools)} from agent '{agent_name}'"
                    )

        # Remove dedicated skill agents (in reverse order to maintain indices)
        for i in reversed(agents_to_remove):
            del config["agents"][i]

        if changes_made:
            with open(yaml_path, "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"Cleaned up {len(changes_made)} references to '{skill_name}' in agents.yaml",
            "changes_made": changes_made,
            "agents_removed": len(agents_to_remove),
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to clean up agents.yaml: {str(e)}"}


def remove_skill_directory(
    skill_name: str, confirmation: str, skills_path: str = "./agent/skills"
) -> Dict[str, Any]:
    """
    Permanently remove a skill directory and all its contents.

    Args:
        skill_name: Name of the skill to remove
        confirmation: User must type "yes" exactly to confirm deletion
        skills_path: Base path to skills directory

    Returns:
        Dictionary with success status and message
    """
    try:
        # Safety check - require explicit confirmation
        # In practice, the agent passes in the confirmation string
        # thus this condition should rarely trigger
        # but this helps provide some validation for manual invocations
        if confirmation.strip().lower() != "yes":
            return {
                "success": False,
                "message": f"Deletion cancelled. To confirm deletion of skill '{skill_name}', you must type exactly 'yes' (case insensitive).",
                "required_confirmation": "yes",
            }

        skills_dir = Path(skills_path)
        skill_directory_path = skills_dir / skill_name

        if not skill_directory_path.exists():
            return {
                "success": False,
                "message": f"Skill directory '{skill_name}' not found at {skill_directory_path}",
            }

        if not skill_directory_path.is_dir():
            return {
                "success": False,
                "message": f"'{skill_name}' exists but is not a directory",
            }

        # Get list of files that will be deleted
        files_to_delete = []
        for item in skill_directory_path.rglob("*"):
            if item.is_file():
                files_to_delete.append(str(item.relative_to(skill_directory_path)))

        shutil.rmtree(skill_directory_path)

        yaml_cleanup_result = remove_skill_from_agents_yaml(skill_name, "./agents.yaml")

        notify_tool_change(
            "skill_removed",
            {
                "skill_name": skill_name,
                "path": str(skill_directory_path),
                "files_deleted": files_to_delete,
                "yaml_cleanup": yaml_cleanup_result,
                "message": f"Skill '{skill_name}' permanently removed",
            },
        )

        cleanup_msg = ""
        if yaml_cleanup_result["success"] and yaml_cleanup_result.get("changes_made"):
            cleanup_msg = f" and cleaned up {len(yaml_cleanup_result['changes_made'])} agent references"

        return {
            "success": True,
            "message": f"Successfully removed skill '{skill_name}' and all its contents{cleanup_msg}",
            "deleted_path": str(skill_directory_path),
            "files_deleted": files_to_delete,
            "file_count": len(files_to_delete),
            "yaml_cleanup": yaml_cleanup_result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to remove skill '{skill_name}': {str(e)}",
        }


def check_dependencies_tool(
    skill_name: str, skills_path: str = "./agent/skills"
) -> Dict[str, Any]:
    """
    Check which dependencies are installed/missing for a skill.

    Args:
        skill_name: Name of the skill to check
        skills_path: Base path to skills directory

    Returns:
        Dictionary with dependency information
    """
    try:
        skill_dir = Path(skills_path) / skill_name

        if not skill_dir.exists():
            return {
                "success": False,
                "message": f"Skill directory not found: {skill_dir}",
            }

        dep_info = get_dependency_info(skill_dir)

        return {"success": True, "skill_name": skill_name, **dep_info}

    except Exception as e:
        return {"success": False, "message": f"Failed to check dependencies: {str(e)}"}


def install_dependencies_tool(
    skill_name: str, skills_path: str = "./agent/skills", confirm: str = "no"
) -> Dict[str, Any]:
    """
    Install missing dependencies for a skill.

    Args:
        skill_name: Name of the skill
        skills_path: Base path to skills directory
        confirm: Must be "yes" to actually install packages

    Returns:
        Dictionary with installation results
    """
    try:
        skill_dir = Path(skills_path) / skill_name

        if not skill_dir.exists():
            return {
                "success": False,
                "message": f"Skill directory not found: {skill_dir}",
            }

        if confirm.lower() != "yes":
            dep_info = get_dependency_info(skill_dir)
            if not dep_info["missing"]:
                return {
                    "success": True,
                    "message": "All dependencies already installed",
                    **dep_info,
                }
            return {
                "success": False,
                "message": f"Would install: {', '.join(dep_info['missing'])}. Set confirm='yes' to proceed.",
                **dep_info,
            }

        # Actually install
        success, message = install_skill_dependencies(skill_dir, auto_confirm=True)

        # Get updated info
        dep_info = get_dependency_info(skill_dir)

        return {
            "success": success,
            "message": message,
            "skill_name": skill_name,
            **dep_info,
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to install dependencies: {str(e)}"}
