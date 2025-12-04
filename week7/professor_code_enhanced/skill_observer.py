"""
Lightweight module for registering skill system observers.

Call register_skill_observers() before creating a ToolBox to enable
automatic skill loading and management.
"""

from pathlib import Path


def register_skill_observers():
    """
    Register observers for skill system auto-loading.

    Call this function BEFORE creating a ToolBox instance to enable:
    - Automatic skill loading when ToolBox is created
    - Skill management tools registration
    - Hot-reloading of skills when they're created/removed
    """
    from tools import register_toolbox_observer, register_tool_change_observer
    from skill_loader import load_all_skill_functions

    def _on_toolbox_created(toolbox):
        """Observer function called when a toolbox is created"""
        # Import here to avoid circular dependency
        import skill_manager

        skill_manager._current_toolbox = toolbox
        skill_manager.register_skill_management_tools(toolbox)

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
        from tools import broadcast_reload_to_all_toolboxes

        if event_type == "skill_created":
            print(f"Skill created: {tool_info.get('skill_name', 'unknown')}")
            broadcast_reload_to_all_toolboxes(source_toolbox)
            _reload_agents_if_available()
        elif event_type == "skill_removed":
            print(f"Skill removed: {tool_info.get('skill_name', 'unknown')}")
            broadcast_reload_to_all_toolboxes(source_toolbox)
            _reload_agents_if_available()

    def _reload_agents_if_available():
        """Attempt to reload agents from agent.py if the function is available"""
        try:
            import agent

            if hasattr(agent, "reload_agents_from_config"):
                agent.reload_agents_from_config()
        except Exception:
            pass

    # Register observers
    register_toolbox_observer(_on_toolbox_created)
    register_tool_change_observer(_on_tool_change)
