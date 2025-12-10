def get_readme_template(skill_name: str) -> str:
    """Generate README template for a new skill."""
    return f"""
    # {skill_name} skill

    Brief description of what this skill does and why it's useful.

    ## Features
    - List key capabilities
    - Highlight important functionality
    - Note any special behaviors

    ## Usage

    Call the tool via the agent system as `{skill_name}_function_name`.

    Python example (direct import):

    ```python
    from agent.skills.{skill_name}.main import your_function

    result = your_function(arg1, arg2)
    print(result)
    ```

    Sample output:
    ```json
    {{
      "success": true,
      "result": "...",
      "message": "..."
    }}
    ```

    ## Functions

    - `{skill_name}_main(input: str) -> dict`: Main skill function

    ## Examples

    ### Example 1: Basic Usage
    ```python
    result = {skill_name}_main("example data")
    # Returns: {{"success": True, "result": "processed output"}}
    ```

    ### Example 2: Error Handling
    ```python
    result = {skill_name}_main("")
    # Returns: {{"success": False, "error": "...", "message": "..."}}
    ```

    ### Example 3: Integration with Other Tools
    ```python
    # Chain with other skills or tools
    data = fetch_data_from_api()
    result = {skill_name}_main(data)
    if result["success"]:
        save_to_database(result["result"])
    ```

    ## Decorator Choice

    **@skill_function** (fast, local execution)
    - Use when: Simple operations, no risky code, performance matters
    - Execution: Runs on host system with timeout protection
    - Speed: Immediate execution
    - Example: Data validation, text processing, calculations

    **@sandbox_skill_function** (secure, isolated execution)  
    - Use when: External libraries, network requests, untrusted operations
    - Execution: Runs in isolated container environment
    - Speed: Slower first run (environment setup), fast subsequent runs
    - Example: Web scraping, file operations, complex data processing
    - **Default choice for new skills** - prioritize security

    ## Configuration

    Document any configuration, environment variables, or dependencies here.
"""


def get_main_py_template(skill_name: str) -> str:
    """Generate main.py template for a new skill."""
    return f'''"""
{skill_name.title()} Skill Implementation

Replace this docstring with a description of what your skill does.

IMPORTANT REQUIREMENTS:
1. All function parameters MUST have type annotations (def func(name: str) -> dict:)
2. For **kwargs, use: **kwargs: Any
3. Import logging if you use logger: import logging; logger = logging.getLogger(__name__)
4. Keep indentation consistent (4 spaces, no tabs)
5. Test imports work: import statements must be at module level or inside functions
6. Avoid undefined variables - all names must be defined before use
7. **RETURN JSON-SERIALIZABLE DATA ONLY**:
   - Return dict, list, str, int, float, bool, or None
   - Convert bytes to base64 strings: base64.b64encode(data).decode('ascii')
   - Or decode to text: data.decode('utf-8')
   - BAD: return {{"content": b"..."}}
   - GOOD: return {{"content_base64": base64.b64encode(data).decode('ascii')}}
   - GOOD: return {{"text": data.decode('utf-8')}}

Note: All function parameters should have type annotations or the skill may load incorrectly.
- Regular parameters: def func(name: str, count: int) -> dict:
- **kwargs parameters: def func(url: str, **kwargs: Any) -> dict:
"""

# Decorator imports with fallback for standalone testing
try:
    from skill_manager import skill_function, sandbox_skill_function
except Exception:
    def skill_function(func):
        func.is_skill_function = True
        return func
    
    def sandbox_skill_function(func):
        func.is_skill_function = True
        func.auto_sandbox = True
        return func

from typing import Optional, Any
import logging

# Setup logging (optional - only if you need logging in your skill)
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Prevents errors if no handler configured

# Use @sandbox_skill_function for security (default choice)
# Use @skill_function for speed when code is simple and trusted
@sandbox_skill_function
def {skill_name}_main(input_data: str) -> dict:
    """
    Main function for the {skill_name} skill.
    
    IMPORTANT: List ALL parameters explicitly in Args section.
    The LLM uses this docstring to understand what parameters are available.
    If a parameter is not listed, the LLM may try to pass parameters that don't exist.
    
    Args:
        input_data (str): Description of input parameter
        
    Returns:
        dict: Dictionary with success status and results
            - success (bool): Whether operation succeeded
            - result (Any): The processed result
            - message (str): Human-readable status message
        
    Example:
        result = {skill_name}_main("example input")
        # Returns: {{"success": True, "result": "processed output"}}
    """
    try:
        # Your skill implementation here
        # This code runs in an isolated sandbox for security
        
        result = {{
            "success": True,
            "input": input_data,
            "result": f"Processed: {{input_data}}",
            "message": "Successfully processed input"
        }}
        
        return result
        
    except Exception as e:
        return {{
            "success": False,
            "error": str(e),
            "message": f"Failed to process input: {{str(e)}}"
        }}


# Example of a function using @skill_function (faster, runs on host)
@skill_function  
def {skill_name}_validate(data: str) -> dict:
    """
    Fast validation function that runs on host system.
    
    Use @skill_function when:
    - Code is simple and trusted
    - No external libraries needed
    - Performance is critical
    - No risky operations
    
    Args:
        data: Data to validate
        
    Returns:
        Validation result dictionary
    """
    if not data or not isinstance(data, str):
        return {{"valid": False, "error": "Invalid input type"}}
    
    return {{
        "valid": True,
        "length": len(data),
        "message": "Input is valid"
    }}


# Real-world examples below - choose the pattern that fits your use case

# Example 1: Web API interaction (uses external library)
@sandbox_skill_function
def {skill_name}_fetch_data(url: str, timeout: int = 10) -> dict:
    """Fetch data from an API endpoint with error handling."""
    import requests
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        return {{
            "success": True,
            "data": response.json(),
            "status_code": response.status_code
        }}
    except requests.exceptions.RequestException as e:
        return {{
            "success": False,
            "error": str(e),
            "url": url
        }}


# Example 2: Data transformation (lightweight, no external deps)
@skill_function
def {skill_name}_transform(items: list) -> dict:
    """Transform and filter a list of items quickly."""
    if not isinstance(items, list):
        return {{"success": False, "error": "Expected list input"}}
    
    # Simple transformation logic
    transformed = [str(item).upper() for item in items if item]
    
    return {{
        "success": True,
        "original_count": len(items),
        "transformed_count": len(transformed),
        "results": transformed
    }}


# Example 3: Complex processing with multiple libraries
@sandbox_skill_function
def {skill_name}_analyze(data: dict) -> dict:
    """Perform analysis requiring multiple external libraries."""
    import json
    from datetime import datetime
    
    try:
        # Complex analysis logic here
        analysis = {{
            "timestamp": datetime.now().isoformat(),
            "data_size": len(json.dumps(data)),
            "keys": list(data.keys()) if isinstance(data, dict) else [],
            "analysis_complete": True
        }}
        
        return {{
            "success": True,
            "analysis": analysis
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e)
        }}
'''
