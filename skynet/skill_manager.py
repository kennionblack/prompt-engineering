import asyncio
from pathlib import Path
import concurrent.futures

from config import load_config

from skill_decorators import (
    DEFAULT_SKILL_TIMEOUT,
    run_with_timeout,
    skill_function,
    sandbox_skill_function,
)

from skill_templates import (
    get_readme_template,
    get_main_py_template,
)

from skill_execution import (
    execute_function_in_sandbox,
)

from skill_loader import (
    load_skill_functions,
    load_all_skill_functions,
    create_skill_wrapper,
)

from skill_lifecycle import (
    create_skill_directory,
    update_agents_yaml_with_skills,
    add_skill_as_tool,
    create_skill_agent,
    check_skill_changes,
    remove_skill_from_agents_yaml,
    remove_skill_directory,
    check_dependencies_tool,
    install_dependencies_tool,
)

from tools import (
    ToolBox,
    register_toolbox_observer,
    register_tool_change_observer,
    broadcast_reload_to_all_toolboxes,
)

from sandbox_manager import (
    execute_skill_code,
)

_current_toolbox: ToolBox = None


# Observer pattern for toolbox creation and tool changes
def _on_toolbox_created(toolbox):
    """Observer function called when a toolbox is created"""
    global _current_toolbox
    _current_toolbox = toolbox
    register_skill_management_tools(toolbox)

    # Register reload callback for this toolbox
    toolbox.register_reload_callback(
        lambda: load_all_skill_functions("./agent/skills", toolbox)
    )

    # Auto-load any existing skills on startup
    skills_dir = Path("./agent/skills")
    if skills_dir.exists():
        load_all_skill_functions(str(skills_dir), toolbox)


def _on_tool_change(event_type: str, tool_info: dict, source_toolbox=None):
    """Observer function called when tools change in any toolbox"""
    if event_type == "skill_created":
        print(f"Skill created: {tool_info.get('skill_name', 'unknown')}")
        # Trigger reload across all toolboxes
        broadcast_reload_to_all_toolboxes(source_toolbox)
        # Reload agents to pick up new skill agents
        _reload_agents_if_available()
    elif event_type == "skill_removed":
        print(f"Skill removed: {tool_info.get('skill_name', 'unknown')}")
        # Trigger reload to remove the deleted skill's tools
        broadcast_reload_to_all_toolboxes(source_toolbox)
        # Reload agents to update tool lists
        _reload_agents_if_available()


def _reload_agents_if_available():
    """Attempt to reload agents from agent.py if the function is available"""
    try:
        import agent

        if hasattr(agent, "reload_agents_from_config"):
            agent.reload_agents_from_config()
    except Exception as e:
        # Silently ignore if agent module isn't loaded yet or function unavailable
        pass


def register_skill_management_tools(toolbox):
    """Register skill management tools with the provided toolbox"""

    @toolbox.tool
    def create_skill(path: str, skill_name: str) -> dict:
        """Create a new skill directory structure with template files.

        IMPORTANT: Use relative path like './agent/skills' or '.' (current directory).
        The function will ensure proper nesting to prevent duplicate
        directory structures. Skills will always be created at the correct
        ./agent/skills/{skill_name} level regardless of input path variations.

        Args:
            path: Base path - use '.' for current directory or './agent/skills'
            skill_name: Name of the skill (will be the directory name)
        """
        return create_skill_directory(path, skill_name)

    @toolbox.tool
    def create_skill_agent_tool(skill_name: str, skill_description: str = "") -> dict:
        """Create a skill agent configuration in agents.yaml"""
        return create_skill_agent(skill_name, skill_description, "./agents.yaml")

    @toolbox.tool
    def refresh_skills() -> dict:
        """
        Refresh all skills AND reload agent tools (use after creating new skill agents).
        This ensures new skill agents are immediately available.

        Returns:
            dict: Result with success status and details about what was reloaded
        """
        # Import here to avoid circular dependency
        from agent_registry import get_current_agents, add_agent_tools
        from agent import tool_box, run_agent

        skills_result = load_all_skill_functions("./agent/skills", toolbox)

        try:
            config = load_config(Path("./agents.yaml"))
            new_agents = {agent["name"]: agent for agent in config["agents"]}

            _current_agents = get_current_agents()
            _current_agents.update(new_agents)

            # Re-register all agent tools (including new skill agents)
            add_agent_tools(new_agents, toolbox, run_agent)

            return {
                "success": True,
                "message": f"Reloaded {skills_result.get('loaded_count', 0)} skill functions and {len(new_agents)} agents",
                "skills_loaded": skills_result.get("loaded_count", 0),
                "agents_registered": len(new_agents),
                "skills_result": skills_result,
            }
        except Exception as e:
            import traceback

            return {
                "success": False,
                "error": f"Failed to reload agents: {str(e)}",
                "traceback": traceback.format_exc(),
                "skills_result": skills_result,
            }

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

    @toolbox.tool
    def list_skills() -> dict:
        """
        List all available skills in the skills directory.

        Returns:
            Dictionary with list of skills and their details
        """
        try:
            skills_dir = Path("./agent/skills")
            if not skills_dir.exists():
                return {
                    "success": True,
                    "message": "No skills directory found",
                    "skills": [],
                    "skill_count": 0,
                }

            skills = []
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                    continue

                skill_info = {"name": skill_dir.name, "path": str(skill_dir)}

                main_py = skill_dir / "main.py"
                skill_info["has_main_py"] = main_py.exists()

                readme = skill_dir / "README.md"
                skill_info["has_readme"] = readme.exists()

                file_count = len([f for f in skill_dir.rglob("*") if f.is_file()])
                skill_info["file_count"] = file_count

                skills.append(skill_info)

            skills.sort(key=lambda x: x["name"])

            return {
                "success": True,
                "message": f"Found {len(skills)} skills",
                "skills": skills,
                "skill_count": len(skills),
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to list skills: {str(e)}"}

    @toolbox.tool
    def remove_skill(skill_name: str, confirmation: str) -> dict:
        """
        Permanently remove a skill and all its files.

        WARNING: This action cannot be undone!

        Args:
            skill_name: Name of the skill directory to remove
            confirmation: Type exactly 'yes' to confirm deletion

        Returns:
            Success/failure status and details of what was removed

        Example:
            remove_skill("old_skill", "yes")  # Removes ./agent/skills/old_skill/
        """
        return remove_skill_directory(skill_name, confirmation, "./agent/skills")

    @toolbox.tool
    def cleanup_agents_yaml_tool(skill_name: str, confirmation: str) -> dict:
        """
        Remove orphaned skill references from agents.yaml without deleting skill files.

        Useful for cleaning up references to skills that were manually deleted.

        Args:
            skill_name: Name of the skill to remove from agents.yaml
            confirmation: Type exactly 'yes' to confirm cleanup

        Returns:
            Success/failure status and details of what was cleaned up

        Example:
            cleanup_agents_yaml_tool("orphaned_skill", "yes")
        """
        if confirmation.strip().lower() != "yes":
            return {
                "success": False,
                "message": f"Cleanup cancelled. To confirm cleanup of '{skill_name}' references, type exactly 'yes'.",
            }

        return remove_skill_from_agents_yaml(skill_name, "./agents.yaml")

    @toolbox.tool
    def execute_sandbox_code(
        skill_name: str,
        code: str,
        language: str = "python",
        libraries: list = None,
        timeout: float = 30,
    ) -> dict:
        """
        Execute code in a persistent sandbox environment for a skill.

        This creates or reuses a sandbox container specifically for the skill
        from a different agent than the skill agent when desired.

        Args:
            skill_name: Name of the skill (for environment isolation)
            code: Code to execute
            language: Programming language ("python", "javascript", "java", "cpp", "go")
            libraries: Additional libraries to install beyond preloaded ones
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with execution results including stdout, stderr, plots

        Example:
            execute_sandbox_code(
                skill_name="data_processor",
                code="import pandas as pd; print(pd.__version__)",
                language="python",
                libraries=["pandas"]
            )
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        execute_skill_code(
                            skill_name, code, language, libraries or [], timeout
                        ),
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    execute_skill_code(
                        skill_name, code, language, libraries or [], timeout
                    )
                )
        except Exception as e:
            return {"success": False, "error": str(e)}

    @toolbox.tool
    def check_skill_dependencies(skill_name: str) -> dict:
        """
        Check which dependencies are installed and missing for a skill.

        Reads the skill's requirements.txt and checks if packages are installed.

        Args:
            skill_name: Name of the skill to check

        Returns:
            Dictionary with:
            - has_requirements: bool (whether requirements.txt exists)
            - total: int (total number of dependencies)
            - installed: List[str] (packages that are installed)
            - missing: List[str] (packages that need to be installed)
            - ready: bool (True if all dependencies are satisfied)

        Example:
            check_skill_dependencies("web_fetch")
            # Returns: {'has_requirements': True, 'total': 3, 'installed': ['requests'],
            #           'missing': ['beautifulsoup4', 'nltk'], 'ready': False}
        """
        return check_dependencies_tool(skill_name)

    @toolbox.tool
    def install_skill_dependencies(skill_name: str, confirm: str = "no") -> dict:
        """
        Install missing dependencies for a skill using pip.

        Reads the skill's requirements.txt and installs any missing packages.
        REQUIRES confirm='yes' to actually install (safety check).

        Args:
            skill_name: Name of the skill
            confirm: Must be exactly 'yes' to proceed with installation

        Returns:
            Dictionary with installation results and updated dependency status

        Example:
            # First check what would be installed:
            install_skill_dependencies("web_fetch")
            # Returns: {'success': False, 'message': 'Would install: nltk. Set confirm="yes" to proceed.'}

            # Then confirm installation:
            install_skill_dependencies("web_fetch", confirm="yes")
            # Returns: {'success': True, 'message': 'Successfully installed 1 packages: nltk', ...}
        """
        return install_dependencies_tool(skill_name, confirm=confirm)


def run_code_in_sandbox(
    skill_name: str,
    code: str,
    language: str = "python",
    libraries: list = None,
    timeout: float = 30,
) -> dict:
    """
    Convenience function for agents to execute code in sandbox.

    This is a standalone function that skills can import and use directly
    without needing access to the toolbox.

    Args:
        skill_name: Name of the skill (for environment isolation)
        code: Code to execute
        language: Programming language ("python", "javascript", "java", "cpp", "go")
        libraries: Additional libraries to install
        timeout: Execution timeout in seconds

    Returns:
        Dictionary with execution results

    Example usage in a skill:
        from skill_manager import run_code_in_sandbox

        result = run_code_in_sandbox(
            skill_name="my_skill",
            code="print('Hello from sandbox!')",
            language="python"
        )
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    execute_skill_code(
                        skill_name, code, language, libraries or [], timeout
                    ),
                )
                return future.result()
        else:
            return loop.run_until_complete(
                execute_skill_code(skill_name, code, language, libraries or [], timeout)
            )
    except RuntimeError:
        return asyncio.run(
            execute_skill_code(skill_name, code, language, libraries or [], timeout)
        )


__all__ = [
    # Decorators
    "skill_function",
    "sandbox_skill_function",
    "DEFAULT_SKILL_TIMEOUT",
    "run_with_timeout",
    # Templates
    "get_readme_template",
    "get_main_py_template",
    # Execution
    "execute_function_in_sandbox",
    "run_code_in_sandbox",
    # Loading
    "load_skill_functions",
    "load_all_skill_functions",
    "create_skill_wrapper",
    # Lifecycle
    "create_skill_directory",
    "update_agents_yaml_with_skills",
    "add_skill_as_tool",
    "create_skill_agent",
    "check_skill_changes",
    "remove_skill_from_agents_yaml",
    "remove_skill_directory",
    # Registration
    "register_skill_management_tools",
]
