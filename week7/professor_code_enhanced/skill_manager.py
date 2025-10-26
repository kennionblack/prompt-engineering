import importlib.util
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Set

from tools import ToolBox, register_toolbox_observer

# Keep track of loaded skills for simple change detection
_loaded_skills: Set[str] = set()
_current_toolbox: ToolBox = None


# Observer pattern implementation - simple and clean!
def _on_toolbox_created(toolbox):
    """Observer function called when a toolbox is created"""
    global _current_toolbox
    _current_toolbox = toolbox
    register_skill_management_tools(toolbox)

    # Auto-load any existing skills on startup
    skills_dir = Path("./agent/skills")
    if skills_dir.exists():
        load_all_skill_functions(str(skills_dir), toolbox)


# Register as observer when module is imported
register_toolbox_observer(_on_toolbox_created)


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


def create_skill_directory(path: str, skill_name: str) -> Dict[str, Any]:
    """Create a skill directory structure with templates."""
    skill_directory_path = Path(path) / "agent" / "skills" / skill_name

    if skill_directory_path.exists():
        return {"success": False, "message": f"Skill {skill_name} already exists"}

    try:
        # Create directory structure
        skill_directory_path.mkdir(parents=True, exist_ok=True)
        scripts_dir = skill_directory_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create README template
        readme_content = f"""# {skill_name.title()} Skill

## Description
Brief description of what this skill does.

## Usage
How to use this skill and what it provides.

## Functions
- `main_function`: Primary function of this skill

## Scripts
Any helper scripts or utilities used by this skill.
"""

        # Create main.py template
        main_py_content = f'''"""
{skill_name.title()} Skill Implementation
"""

from pathlib import Path

# These will be injected by the skill manager when functions are called
# SKILL_DIR: Path to this skill directory
# SKILL_NAME: Name of this skill

def get_skill_readme():
    """Load skill README on demand."""
    readme_path = SKILL_DIR / "README.md"
    if readme_path.exists():
        return readme_path.read_text()
    return f"No README found for skill {{SKILL_NAME}}"

def get_skill_scripts():
    """Get list of available scripts in this skill."""
    scripts_dir = SKILL_DIR / "scripts"
    if scripts_dir.exists():
        return list(scripts_dir.glob("*.py"))
    return []

# Import the decorator from skill_manager
from skill_manager import skill_function

@skill_function
def {skill_name}_main(input_data: str) -> dict:
    """
    Main function for the {skill_name} skill.
    
    Args:
        input_data: Input data to process
        
    Returns:
        Dictionary with processing results
    """
    # Context loaded only when called (lazy loading)
    readme = get_skill_readme()
    scripts = get_skill_scripts()
    
    return {{
        "success": True,
        "skill": SKILL_NAME,
        "input_length": len(input_data),
        "readme_length": len(readme),
        "available_scripts": [s.name for s in scripts],
        "message": f"Processed by {{SKILL_NAME}} skill"
    }}

@skill_function
def get_{skill_name}_info() -> dict:
    """Get information about this skill."""
    readme = get_skill_readme()
    scripts = get_skill_scripts()
    
    return {{
        "skill_name": SKILL_NAME,
        "skill_directory": str(SKILL_DIR),
        "readme_preview": readme[:200] + "..." if len(readme) > 200 else readme,
        "available_scripts": [s.name for s in scripts],
        "functions": ["{skill_name}_main", "get_{skill_name}_info"]
    }}
'''

        (skill_directory_path / "README.md").write_text(readme_content)
        (skill_directory_path / "main.py").write_text(main_py_content)

        return {
            "success": True,
            "message": f"Created skill directory structure for {skill_name}",
            "path": str(skill_directory_path),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create skill directory: {str(e)}",
        }


def load_skill_functions(
    skill_name: str, skills_path: str = "./agent/skills", tool_box: ToolBox = None
) -> Dict[str, Any]:
    """
    Load and register functions from a specific skill directory.

    This implementation provides true lazy loading - only function signatures
    are loaded initially, with full skill context loaded on-demand when called.

    Args:
        skill_name: Name of the skill directory
        skills_path: Base path to skills directory
        tool_box: ToolBox instance to register functions with

    Returns:
        Dictionary with success status and loaded functions info
    """
    if tool_box is None:
        return {"success": False, "message": "ToolBox instance required"}

    try:
        skill_dir = Path(skills_path) / skill_name

        if not skill_dir.exists():
            return {
                "success": False,
                "message": f"Skill directory not found: {skill_dir}",
            }

        # Look for main.py in the skill directory
        main_py = skill_dir / "main.py"
        if not main_py.exists():
            return {
                "success": False,
                "message": f"No main.py found in skill {skill_name}",
            }

        # Dynamically import the skill module
        module_name = f"skill_{skill_name}"
        spec = importlib.util.spec_from_file_location(module_name, main_py)

        if not spec or not spec.loader:
            return {
                "success": False,
                "message": f"Could not load module spec for {skill_name}",
            }

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

            if (
                callable(attr)
                and hasattr(attr, "is_skill_function")
                and not attr_name.startswith("_")
            ):

                # Create a wrapper that provides skill context
                def create_skill_wrapper(skill_func, skill_dir_path, skill_name_ref):
                    def skill_wrapper(*args, **kwargs):
                        # This is where lazy loading happens - context loaded only when called
                        print(
                            f"🔧 Executing skill function: {skill_func.__name__} from {skill_name_ref}"
                        )

                        # Inject skill directory path into the function's context
                        if hasattr(skill_func, "__globals__"):
                            skill_func.__globals__["SKILL_DIR"] = skill_dir_path
                            skill_func.__globals__["SKILL_NAME"] = skill_name_ref

                        return skill_func(*args, **kwargs)

                    # Preserve function metadata for tool registration
                    skill_wrapper.__name__ = f"{skill_name}_{skill_func.__name__}"
                    skill_wrapper.__doc__ = (
                        skill_func.__doc__ or f"Skill function from {skill_name}"
                    )
                    skill_wrapper.__annotations__ = getattr(
                        skill_func, "__annotations__", {}
                    )

                    return skill_wrapper

                # Create the wrapper and register it as a tool
                wrapped_function = create_skill_wrapper(attr, skill_dir, skill_name)
                tool_box.tool(wrapped_function)

                functions_registered.append(
                    {
                        "name": wrapped_function.__name__,
                        "original_name": attr_name,
                        "doc": wrapped_function.__doc__,
                    }
                )

        return {
            "success": True,
            "message": f"Loaded {len(functions_registered)} functions from skill {skill_name}",
            "functions": functions_registered,
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to load skill functions: {str(e)}"}


def load_all_skill_functions(
    skills_path: str = "./agent/skills", tool_box: ToolBox = None
) -> Dict[str, Any]:
    """
    Scan the skills directory and load all skill functions as tools.

    This provides true lazy loading - only function signatures are loaded initially,
    with skill context loaded on-demand when functions are called.

    Args:
        skills_path: Path to the skills directory
        tool_box: ToolBox instance to register functions with

    Returns:
        Dictionary with success status and list of loaded skill functions
    """
    if tool_box is None:
        return {"success": False, "message": "ToolBox instance required"}

    try:
        skills_dir = Path(skills_path)
        if not skills_dir.exists():
            return {
                "success": False,
                "message": f"Skills directory not found: {skills_dir}",
            }

        loaded_skills = []
        total_functions = 0

        # Track what skills are available now
        current_skills = set()

        # Scan each subdirectory in the skills directory
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            current_skills.add(skill_dir.name)

            # Load functions from this skill
            result = load_skill_functions(skill_dir.name, skills_path, tool_box)
            if result["success"]:
                loaded_skills.append(
                    {"name": skill_dir.name, "functions": result.get("functions", [])}
                )
                function_count = len(result.get("functions", []))
                total_functions += function_count
                print(f"Loaded {function_count} functions from skill: {skill_dir.name}")
            else:
                print(f"Failed to load skill {skill_dir.name}: {result['message']}")

        # Update our tracking of loaded skills
        global _loaded_skills
        new_skills = current_skills - _loaded_skills
        removed_skills = _loaded_skills - current_skills
        _loaded_skills = current_skills

        status_info = []
        if new_skills:
            status_info.append(f"New skills: {', '.join(new_skills)}")
        if removed_skills:
            status_info.append(f"Removed skills: {', '.join(removed_skills)}")

        return {
            "success": True,
            "message": f"Loaded {total_functions} functions from {len(loaded_skills)} skills",
            "loaded_skills": loaded_skills,
            "total_functions": total_functions,
            "changes": status_info,
            "new_skills": list(new_skills),
            "removed_skills": list(removed_skills),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to load skill functions: {str(e)}",
        }


def add_skill_as_tool(
    agents_yaml_path: str, skill_name: str, skill_description: str
) -> Dict[str, Any]:
    """
    Add a skill as a tool to the agents.yaml configuration file and persist it.

    This function modifies the existing agents.yaml file to include the new skill
    in the tools array, implementing functionality similar to Anthropic's Skills concept.

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

        # Read the current YAML configuration
        with open(agents_yaml_file, "r") as file:
            config = yaml.safe_load(file)

        # Find all agents and add the skill to their tools if not already present
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

        # Write the updated configuration back to the file
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
            "kwargs": {"max_tokens": 4000},
        }

        # Load existing config or create new one
        if agents_yaml_file.exists():
            with open(agents_yaml_file, "r") as file:
                config = yaml.safe_load(file) or {}
        else:
            config = {"agents": [], "main": "user_interface"}

        if "agents" not in config:
            config["agents"] = []

        # Check if agent already exists
        existing_agent = None
        for i, agent in enumerate(config["agents"]):
            if agent.get("name") == skill_agent["name"]:
                existing_agent = i
                break

        # Add or update the agent
        if existing_agent is not None:
            config["agents"][existing_agent] = skill_agent
            action = "Updated"
        else:
            config["agents"].append(skill_agent)
            action = "Added"

        # Write back to file
        with open(agents_yaml_file, "w") as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"{action} skill agent '{skill_agent['name']}' in {agents_yaml_file.name}",
            "agent_config": skill_agent,
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to create skill agent: {str(e)}"}


def check_skill_changes(skills_path: str = "./agent/skills") -> Dict[str, Any]:
    """
    Check for changes in the skills directory without reloading.
    Simple, lightweight alternative to file watching.
    """
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
        global _loaded_skills
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


def register_skill_management_tools(toolbox):
    """Register skill management tools with the provided toolbox"""

    @toolbox.tool
    def create_skill(path: str, skill_name: str) -> dict:
        """Create a new skill directory structure with template files"""
        return create_skill_directory(path, skill_name)

    @toolbox.tool
    def register_skill_as_tool(skill_name: str, skill_description: str = "") -> dict:
        """Register a skill as a tool by adding it to agents.yaml"""
        return add_skill_as_tool("./agents.yaml", skill_name, skill_description)

    @toolbox.tool
    def create_skill_agent_tool(skill_name: str, skill_description: str = "") -> dict:
        """Create a skill agent configuration in agents.yaml"""
        return create_skill_agent("./agents.yaml", skill_name, skill_description)

    @toolbox.tool
    def refresh_skills() -> dict:
        """Refresh all skills by reloading skill functions"""
        return load_all_skill_functions("./agent/skills", toolbox)

    @toolbox.tool
    def check_for_skill_changes() -> dict:
        """Check if there are new or removed skills without reloading"""
        return check_skill_changes("./agent/skills")

    @toolbox.tool
    def sync_skills() -> dict:
        """Check for changes and reload skills if any are found"""
        changes = check_skill_changes("./agent/skills")
        if not changes["success"]:
            return changes

        if changes["has_changes"]:
            # Reload skills since there are changes
            result = load_all_skill_functions("./agent/skills", toolbox)
            result["detected_changes"] = {
                "new_skills": changes["new_skills"],
                "removed_skills": changes["removed_skills"],
            }
            return result
        else:
            return {
                "success": True,
                "message": "No skill changes detected - no reload needed",
                "has_changes": False,
            }
