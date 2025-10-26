# Example skill main.py file
# This shows how to create skill functions with Approach B

from pathlib import Path

# SKILL_DIR and SKILL_NAME will be injected by the wrapper when called
# SKILL_DIR = Path(__file__).parent  # This gets set dynamically
# SKILL_NAME = "example_skill"        # This gets set dynamically


def get_skill_readme():
    """Helper to load README only when needed (lazy loading)"""
    readme_path = SKILL_DIR / "README.md"
    if readme_path.exists():
        return readme_path.read_text()
    return f"No README found for skill {SKILL_NAME}"


def get_skill_scripts():
    """Helper to list available scripts"""
    scripts_dir = SKILL_DIR / "scripts"
    if scripts_dir.exists():
        return list(scripts_dir.glob("*.py"))
    return []


# Mark functions with @skill_function decorator to export them as tools


def skill_function(func):
    """Local decorator - this gets imported from agent.py in real usage"""
    func.is_skill_function = True
    return func


@skill_function
def process_data(input_data: str, operation: str = "analyze") -> dict:
    """
    Process data using this skill's specialized knowledge and scripts.

    Args:
        input_data: The data to process
        operation: Type of operation to perform (analyze, transform, validate)

    Returns:
        Dictionary with processing results
    """
    # Context is loaded only when this function is called!
    readme_content = get_skill_readme()
    available_scripts = get_skill_scripts()

    # Use the skill's knowledge and scripts
    result = {
        "success": True,
        "operation": operation,
        "input_length": len(input_data),
        "skill_info": f"Processed using {SKILL_NAME} skill",
        "available_scripts": [s.name for s in available_scripts],
        "skill_readme_length": len(readme_content),
    }

    # This is where you'd run actual processing using scripts in SKILL_DIR
    if operation == "analyze":
        result["analysis"] = f"Analysis of {len(input_data)} characters"
    elif operation == "transform":
        result["transformed"] = input_data.upper()

    return result


@skill_function
def get_skill_info() -> dict:
    """Get information about this skill and its capabilities."""
    readme_content = get_skill_readme()
    scripts = get_skill_scripts()

    return {
        "skill_name": SKILL_NAME,
        "skill_directory": str(SKILL_DIR),
        "readme_preview": (
            readme_content[:200] + "..." if len(readme_content) > 200 else readme_content
        ),
        "available_scripts": [s.name for s in scripts],
        "capabilities": ["process_data", "get_skill_info"],
    }
