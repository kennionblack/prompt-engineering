import importlib.util
import sys
import yaml
import threading
from pathlib import Path
from typing import Dict, Any, Set, Callable

from tools import (
    ToolBox,
    register_toolbox_observer,
    register_tool_change_observer,
    notify_tool_change,
    broadcast_reload_to_all_toolboxes,
)
from sandbox_manager import (
    get_sandbox_manager,
    execute_skill_code,
    get_skill_environment_info,
    cleanup_skill_environment,
)

# Keep track of loaded skills for simple change detection
_loaded_skills: Set[str] = set()
_current_toolbox: ToolBox = None

# Default timeout for skill function execution (in seconds)
# This is needed unless you've solved the halting problem
DEFAULT_SKILL_TIMEOUT = 30


def run_with_timeout(func, timeout_seconds=DEFAULT_SKILL_TIMEOUT, *args, **kwargs):
    """
    Execute a function with a timeout. Returns the result or raises TimeoutError.

    Args:
        func: Function to execute
        timeout_seconds: Maximum execution time in seconds
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Function result

    Raises:
        TimeoutError: If function execution exceeds timeout
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Thread is still running, function timed out
        raise TimeoutError(
            f"Skill function execution timed out after {timeout_seconds} seconds"
        )

    if exception[0]:
        raise exception[0]

    return result[0]


# Observer pattern implementation - simple and clean!
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
        print(f"🔔 Skill created: {tool_info.get('skill_name', 'unknown')}")
        # Trigger reload across all toolboxes
        broadcast_reload_to_all_toolboxes(source_toolbox)
    elif event_type == "skill_removed":
        print(f"🗑️  Skill removed: {tool_info.get('skill_name', 'unknown')}")
        # Trigger reload to remove the deleted skill's tools
        broadcast_reload_to_all_toolboxes(source_toolbox)


# Register as observers when module is imported
register_toolbox_observer(_on_toolbox_created)
register_tool_change_observer(_on_tool_change)


def skill_function(func: Callable) -> Callable:
    """Decorator that marks a function as a skill function."""
    func.is_skill_function = True
    return func


def sandbox_skill_function(func: Callable) -> Callable:
    """
    Decorator that marks a function as a skill function with automatic sandbox execution.

    Functions decorated with this will automatically execute their entire code
    in a secure sandbox environment instead of the host system.

    Benefits:
    - Complete isolation from host system
    - Automatic security and resource limiting
    - All dependencies handled in sandbox
    - Can still access SKILL_DIR and SKILL_NAME variables

    Use this when:
    - Function performs complex computations
    - Function might have security implications
    - Function needs specific library versions
    - You want maximum isolation

    Example:
        @sandbox_skill_function
        def process_data(data):
            import pandas as pd
            df = pd.DataFrame(data)
            return df.describe().to_dict()
    """
    func.is_skill_function = True
    func.auto_sandbox = True  # Flag for automatic sandbox execution
    return func


def create_skill_directory(path: str, skill_name: str) -> Dict[str, Any]:
    """Create a skill directory structure with templates."""
    # Convert path to Path object and resolve any relative paths
    base_path = Path(path).resolve()

    # Strict path validation to prevent nested directories
    # Always ensure we're working at the correct agent/skills level
    if str(base_path).endswith("agent/skills"):
        # Perfect - we're at the skills directory level
        skill_directory_path = base_path / skill_name
    elif "agent/skills" in str(base_path):
        # We're somewhere inside agent/skills - extract the base and rebuild
        path_parts = base_path.parts
        agent_skills_index = None
        for i, part in enumerate(path_parts):
            if part == "skills" and i > 0 and path_parts[i - 1] == "agent":
                agent_skills_index = i
                break

        if agent_skills_index is not None:
            # Reconstruct path up to agent/skills level
            base_parts = path_parts[: agent_skills_index + 1]
            skills_base = Path(*base_parts)
            skill_directory_path = skills_base / skill_name
        else:
            # Fallback - append to provided path
            skill_directory_path = base_path / "agent" / "skills" / skill_name
    else:
        # No agent/skills in path - append the full structure
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
        # Log where we're creating the skill for debugging
        print(f"🔧 Creating skill '{skill_name}' at: {skill_directory_path}")

        # Create directory structure
        skill_directory_path.mkdir(parents=True, exist_ok=True)
        scripts_dir = skill_directory_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create README template
        readme_content = f"""# {skill_name.title()} Skill

## Description
Brief description of what this skill does.

## Usage
This skill provides secure code execution through persistent sandbox environments.

### Available Functions
- `{skill_name}_main(input_data: str)`: Main skill function with example sandbox usage
- `{skill_name}_code_executor(code: str, language: str, libraries: list)`: Execute arbitrary code
- `get_{skill_name}_info()`: Get skill information and capabilities

### Usage Examples

#### Manual Sandbox Control
```python
# Execute specific code in sandbox
result = {skill_name}_code_executor('''
import json
data = {{"message": "Hello from sandbox!"}}
print(json.dumps(data, indent=2))
''', language="python", libraries=["requests"])
```

#### Automatic Sandbox Execution  
```python
# Call function that runs entirely in sandbox automatically
result = {skill_name}_auto_sandbox_demo([1, 2, 3, 4, 5])
# Entire function executes in secure container
```

## Sandbox Execution Modes

This skill supports two sandbox execution approaches:

### 1. Manual Sandbox Control (`@skill_function`)
- Function runs on host system
- Can manually execute code in sandbox using tools
- More control over what gets sandboxed
- Good for mixed host/sandbox operations

### 2. Automatic Sandbox Execution (`@sandbox_skill_function`)  
- Entire function runs in secure container
- No manual sandbox calls needed
- Maximum security and isolation
- Perfect for pure computational tasks

## Sandbox Features
This skill includes persistent sandbox execution capabilities:

### ✅ **Performance**
- **Persistent environments** - No container startup delay after first use
- **Preloaded libraries** - Common libraries ready to use
- **Environment pooling** - Efficient resource management

### 🔒 **Security** 
- **Isolated execution** - Complete separation from host system
- **Resource limits** - Memory, CPU, and time constraints
- **Network isolation** - Controlled external access

### 🛠️ **Capabilities**
- **Multi-language support** - Python, JavaScript, Java, C++, Go
- **Library installation** - Install packages on-demand
- **Plot/visualization capture** - Automatic image generation
- **Output streaming** - Real-time stdout/stderr capture

### 📚 **Preloaded Libraries**

**Python Environment:**
- `requests` - HTTP requests
- `json` - JSON handling
- `pathlib` - Path operations  
- `datetime` - Date/time operations
- `os` - Operating system interface
- `sys` - System parameters

**JavaScript Environment:**
- `axios` - HTTP client
- `lodash` - Utility functions
- `moment` - Date/time manipulation

## Examples

### Data Processing
```python
code = '''
import pandas as pd
import json

# Sample data processing
data = {{"values": [1, 2, 3, 4, 5]}}
df = pd.DataFrame(data)
result = df.describe().to_dict()
print(json.dumps(result, indent=2))
'''

result = await {skill_name}_code_executor(code, libraries=["pandas"])
```

### Web Requests
```python
code = '''
import requests
import json

response = requests.get("https://api.github.com/users/octocat")
data = response.json()
print(f"User: {{data.get('name', 'Unknown')}}")
'''

result = await {skill_name}_code_executor(code)
```

### Visualization
```python
code = '''
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title("Sine Wave")
plt.show()  # Plot will be automatically captured
'''

result = await {skill_name}_code_executor(code, libraries=["matplotlib", "numpy"])
```

## Documentation
For complete sandbox usage guide, see `SANDBOX_GUIDE.md` in the project root.

## Scripts
Any helper scripts or utilities used by this skill are stored in the `scripts/` directory.
"""

        # Create main.py template with sandbox integration
        main_py_content = f'''"""
{skill_name.title()} Skill Implementation with Sandbox Support
"""

from pathlib import Path
from skill_manager import run_code_in_sandbox

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

# Provide noop decorators if skill system's decorators aren't available in this environment
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

@skill_function
def {skill_name}_main(input_data: str) -> dict:
    """
    Main function for the {skill_name} skill.
    
    This demonstrates how to use the persistent sandbox environment
    for secure code execution with preloaded libraries.
    
    Args:
        input_data: Input data to process
        
    Returns:
        Dictionary with processing results including sandbox execution
    """
    # Context loaded only when called (lazy loading)
    readme = get_skill_readme()
    scripts = get_skill_scripts()
    
    # Example: Process data in persistent sandbox environment
    # The sandbox provides isolated, secure execution with preloaded libraries
    processing_code = """
import json
import datetime
import hashlib

# Process the input data safely
input_text = """ + repr(input_data) + """

# Analyze the input
analysis = {{
    "processed_at": datetime.datetime.now().isoformat(),
    "input_length": len(input_text),
    "input_hash": hashlib.md5(input_text.encode()).hexdigest()[:8],
    "input_preview": input_text[:100] + "..." if len(input_text) > 100 else input_text,
    "word_count": len(input_text.split()) if input_text else 0,
    "processing_complete": True
}}

# Output results
print("=== Processing Results ===")
print(json.dumps(analysis, indent=2))
print(f"Input successfully processed: {{analysis['input_length']}} characters")
"""
    
    # Execute in persistent sandbox (fast after first use)
    sandbox_result = run_code_in_sandbox(
        skill_name=SKILL_NAME,
        code=processing_code,
        language="python",
        libraries=["requests"],  # Additional libraries beyond preloaded ones
        timeout=30
    )
    
    # Parse sandbox output if successful
    processed_data = None
    if sandbox_result.get("success") and sandbox_result.get("stdout"):
        try:
            # Extract JSON from stdout (basic parsing)
            stdout_lines = sandbox_result["stdout"].strip().split("\\n")
            for line in stdout_lines:
                if line.strip().startswith("{{"):
                    processed_data = json.loads(line.strip())
                    break
        except Exception:
            processed_data = {{"parse_error": "Could not parse sandbox output"}}
    
    return {{
        "success": True,
        "skill": SKILL_NAME,
        "input_length": len(input_data),
        "readme_length": len(readme),
        "available_scripts": [s.name for s in scripts],
        "sandbox_execution": sandbox_result,
        "processed_data": processed_data,
        "environment_info": {{
            "persistent": True,
            "preloaded_libraries": ["requests", "json", "pathlib", "datetime", "os", "sys"],
            "execution_count": sandbox_result.get("execution_count", 0)
        }},
        "message": f"Processed by {{SKILL_NAME}} skill with persistent sandbox (execution #{{sandbox_result.get('execution_count', 0)}})"
    }}

@skill_function
def {skill_name}_code_executor(code: str, language: str = "python", libraries: list = None) -> dict:
    """
    Execute arbitrary code in this skill's persistent sandbox environment.
    
    This provides direct access to the sandbox for running custom code.
    Perfect for data processing, analysis, or any computational tasks.
    
    Args:
        code: Code to execute
        language: Programming language (python, javascript, java, cpp, go)
        libraries: Additional libraries to install beyond preloaded ones
        
    Returns:
        Dictionary with execution results including stdout, stderr, plots
        
    Example:
        # Execute Python data analysis
        result = {skill_name}_code_executor(
            code='import pandas as pd; print("Hello from sandbox!")',
            language="python"
        )
        
        # Execute JavaScript  
        result = {skill_name}_code_executor(
            code='console.log("Hello from JavaScript sandbox!");',
            language="javascript"
        )
    """
    return run_code_in_sandbox(
        skill_name=SKILL_NAME,
        code=code,
        language=language,
        libraries=libraries or [],
        timeout=60
    )

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
        "functions": ["{skill_name}_main", "{skill_name}_code_executor", "get_{skill_name}_info", "{skill_name}_auto_sandbox_demo"],
        "sandbox_enabled": True,
        "supported_languages": ["python", "javascript", "java", "cpp", "go"]
    }}

@sandbox_skill_function
def {skill_name}_auto_sandbox_demo(data: list) -> dict:
    """
    Demonstration of automatic sandbox execution.
    
    This function runs entirely in a secure sandbox container automatically.
    No need to manually call sandbox tools - the entire function executes in isolation.
    
    Args:
        data: List of numbers to process
        
    Returns:
        Dictionary with statistical analysis
    """
    # This entire function runs in sandbox automatically!
    # All imports and operations are sandboxed
    import statistics
    import math
    
    if not data or not all(isinstance(x, (int, float)) for x in data):
        return {{"error": "Invalid input: expected list of numbers"}}
    
    # Perform statistical analysis
    analysis = {{
        "count": len(data),
        "sum": sum(data),
        "mean": statistics.mean(data),
        "median": statistics.median(data),
        "std_dev": statistics.stdev(data) if len(data) > 1 else 0,
        "min": min(data),
        "max": max(data),
        "geometric_mean": math.exp(sum(math.log(x) for x in data if x > 0) / len([x for x in data if x > 0])) if any(x > 0 for x in data) else 0
    }}
    
    return {{
        "success": True,
        "analysis": analysis,
        "note": "This analysis was performed entirely in a secure sandbox container",
        "skill": SKILL_NAME
    }}
'''

        (skill_directory_path / "README.md").write_text(readme_content)
        (skill_directory_path / "main.py").write_text(main_py_content)

        # Notify all toolboxes that a new skill was created
        notify_tool_change(
            "skill_created",
            {
                "skill_name": skill_name,
                "path": str(skill_directory_path),
                "message": f"New skill '{skill_name}' created",
            },
        )

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


def execute_function_in_sandbox(skill_func, skill_name, skill_dir, *args, **kwargs):
    """
    Execute an entire skill function in a sandbox environment.

    This serializes the function call, executes it in the sandbox, and returns the result.
    Automatically extracts module-level imports from the skill file.
    """
    import inspect
    import json
    import ast
    import re

    # Get function source code
    try:
        func_source = inspect.getsource(skill_func)
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not extract function source: {e}",
            "message": "Function cannot be executed in sandbox - use manual sandbox calls instead",
        }

    # Extract module-level imports from the skill's module
    module_imports = []
    try:
        # Get the module source
        module = inspect.getmodule(skill_func)
        if module and hasattr(module, "__file__") and module.__file__:
            module_source = inspect.getsource(module)

            # Parse the module to extract import statements
            tree = ast.parse(module_source)
            for node in tree.body:
                if isinstance(node, ast.Import):
                    # Handle: import module, import module as alias
                    for alias in node.names:
                        if alias.asname:
                            module_imports.append(
                                f"import {alias.name} as {alias.asname}"
                            )
                        else:
                            module_imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    # Handle: from module import name, from module import name as alias
                    module_name = node.module or ""
                    names = []
                    for alias in node.names:
                        if alias.asname:
                            names.append(f"{alias.name} as {alias.asname}")
                        else:
                            names.append(alias.name)
                    module_imports.append(f"from {module_name} import {', '.join(names)}")
    except Exception as e:
        print(f"⚠️  Could not extract module imports: {e}")

    # Build import section (filter out skill_manager imports which aren't needed in sandbox)
    import_section = "\n".join(
        [
            imp
            for imp in module_imports
            if not imp.startswith("from skill_manager import")
            and not imp.startswith("import skill_manager")
        ]
    )

    # Create a sandbox execution script
    execution_script = f"""
import json
import sys
from pathlib import Path

# Set up skill context
SKILL_DIR = Path("{skill_dir}")
SKILL_NAME = "{skill_name}"

# Define stub decorators
# It's easier to have no-op decorators than modify the ast parsing
def skill_function(func):
    return func

def sandbox_skill_function(func):
    return func

# Module-level imports from skill file
{import_section}

# Function source code
{func_source}

# Arguments passed to function
args = {repr(list(args)) if args else "[]"}
kwargs = {repr(kwargs) if kwargs else "{{}}"}

try:
    # Execute the function
    result = {skill_func.__name__}(*args, **kwargs)
    
    # Return the result as JSON
    output = {{
        "success": True,
        "result": result,
        "function": "{skill_func.__name__}",
        "skill": "{skill_name}"
    }}
    print("SANDBOX_RESULT:", json.dumps(output))
    
except Exception as e:
    # Return error information
    import traceback
    error_output = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc(),
        "function": "{skill_func.__name__}",
        "skill": "{skill_name}"
    }}
    print("SANDBOX_RESULT:", json.dumps(error_output))
"""

    # Extract library names from imports for sandbox installation
    # List of Python standard library modules that don't need installation
    stdlib_modules = {
        "json",
        "sys",
        "os",
        "pathlib",
        "datetime",
        "time",
        "traceback",
        "typing",
        "collections",
        "base64",
        "hashlib",
        "re",
        "math",
        "random",
        "string",
        "itertools",
        "functools",
        "operator",
        "copy",
        "pickle",
        "io",
        "tempfile",
        "shutil",
        "glob",
        "fnmatch",
        "linecache",
        "struct",
        "codecs",
        "locale",
        "gettext",
        "logging",
        "platform",
        "errno",
        "ctypes",
        "abc",
        "atexit",
        "warnings",
        "contextlib",
        "weakref",
        "array",
        "bisect",
        "heapq",
        "enum",
        "decimal",
        "fractions",
        "statistics",
        "unicodedata",
        "textwrap",
        "inspect",
        "ast",
        "dis",
        "importlib",
        "pkgutil",
        "zipimport",
        "threading",
        "multiprocessing",
        "subprocess",
        "queue",
        "asyncio",
        "socket",
        "ssl",
        "email",
        "urllib",
        "http",
        "html",
        "xml",
        "csv",
        "configparser",
        "argparse",
        "getopt",
        "pprint",
        "reprlib",
    }

    libraries = []
    for imp in module_imports:
        if imp.startswith("import "):
            # Extract base module name from "import requests" or "import requests as req"
            lib = imp.split()[1].split(" as ")[0].split(".")[0]
            if lib not in stdlib_modules:
                libraries.append(lib)
        elif imp.startswith("from ") and " import " in imp:
            # Extract base module from "from requests import Session"
            lib = imp.split("from ")[1].split(" import")[0].strip().split(".")[0]
            if lib and lib not in stdlib_modules:
                libraries.append(lib)

    # Remove duplicates
    libraries = list(set(libraries))

    if libraries:
        print(f"📦 Detected libraries for sandbox: {', '.join(libraries)}")

    # Execute in sandbox with detected libraries
    sandbox_result = run_code_in_sandbox(
        skill_name=skill_name,
        code=execution_script,
        language="python",
        libraries=libraries,
        timeout=60,
    )

    # Parse the result from sandbox output
    if sandbox_result.get("success") and sandbox_result.get("stdout"):
        stdout_lines = sandbox_result["stdout"].split("\n")
        for line in stdout_lines:
            if line.startswith("SANDBOX_RESULT:"):
                try:
                    result_json = line.replace("SANDBOX_RESULT:", "").strip()
                    parsed_result = json.loads(result_json)

                    if parsed_result.get("success"):
                        return parsed_result["result"]
                    else:
                        print(f"❌ Sandbox execution error: {parsed_result.get('error')}")
                        return {
                            "success": False,
                            "error": parsed_result.get("error"),
                            "traceback": parsed_result.get("traceback"),
                        }
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse sandbox result: {e}")

    # Fallback - return sandbox execution details
    return {
        "success": False,
        "error": "Sandbox execution failed or produced no parseable output",
        "sandbox_details": sandbox_result,
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
                    import functools
                    import inspect

                    # Check if skill function should run in sandbox automatically
                    auto_sandbox = getattr(skill_func, "auto_sandbox", False)

                    @functools.wraps(skill_func)
                    def skill_wrapper(*args, **kwargs):
                        # This is where lazy loading happens - context loaded only when called
                        print(
                            f"🔧 Executing skill function: {skill_func.__name__} from {skill_name_ref}"
                        )

                        # Inject skill directory path into the function's context
                        if hasattr(skill_func, "__globals__"):
                            skill_func.__globals__["SKILL_DIR"] = skill_dir_path
                            skill_func.__globals__["SKILL_NAME"] = skill_name_ref

                        # Get timeout from function attribute or use default
                        timeout = getattr(skill_func, "timeout", DEFAULT_SKILL_TIMEOUT)

                        try:
                            # If auto_sandbox is enabled, execute the entire function in sandbox
                            if auto_sandbox:
                                return run_with_timeout(
                                    execute_function_in_sandbox,
                                    timeout,
                                    skill_func,
                                    skill_name_ref,
                                    skill_dir_path,
                                    *args,
                                    **kwargs,
                                )
                            else:
                                # Normal execution with timeout - function can manually use sandbox tools
                                return run_with_timeout(
                                    skill_func, timeout, *args, **kwargs
                                )
                        except TimeoutError as e:
                            return {
                                "success": False,
                                "error": str(e),
                                "message": f"Skill function {skill_func.__name__} timed out after {timeout} seconds. Consider optimizing the function or increasing timeout.",
                            }

                    # Update the wrapper name to include the skill
                    skill_wrapper.__name__ = f"{skill_name}_{skill_func.__name__}"

                    # Ensure the wrapper has the exact same signature as the original function
                    skill_wrapper.__signature__ = inspect.signature(skill_func)

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

        # Track skill functions for agents.yaml update
        skill_function_map = {}

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

                # Track function names for agents.yaml update
                function_names = [func["name"] for func in result.get("functions", [])]
                skill_function_map[skill_dir.name] = function_names

                print(f"Loaded {function_count} functions from skill: {skill_dir.name}")
            else:
                print(f"Failed to load skill {skill_dir.name}: {result['message']}")

        # Update agents.yaml with skill functions
        yaml_update_result = {"success": True, "message": "No skills to update"}
        if skill_function_map:
            yaml_update_result = update_agents_yaml_with_skills(skill_function_map)
            if yaml_update_result["success"]:
                print(f"📝 {yaml_update_result['message']}")
            else:
                print(f"⚠️ Failed to update agents.yaml: {yaml_update_result['message']}")

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
            "yaml_update": yaml_update_result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to load skill functions: {str(e)}",
        }


def update_agents_yaml_with_skills(
    skill_function_map: dict, agents_yaml_path: str = "./agents.yaml"
):
    """
    Update agents.yaml to include skill functions in agent tool lists.

    Args:
        skill_function_map: Dictionary mapping skill_name -> [function_names]
        agents_yaml_path: Path to agents.yaml file
    """
    try:
        agents_yaml_file = Path(agents_yaml_path)
        if not agents_yaml_file.exists():
            return {
                "success": False,
                "message": f"agents.yaml not found at {agents_yaml_path}",
            }

        # Load current config
        with open(agents_yaml_file, "r") as file:
            config = yaml.safe_load(file) or {}

        if "agents" not in config:
            return {"success": False, "message": "No agents section found in agents.yaml"}

        # Get all skill function names
        all_skill_functions = []
        for skill_name, function_names in skill_function_map.items():
            all_skill_functions.extend(function_names)

        modified_agents = []

        for agent in config["agents"]:
            agent_name = agent.get("name", "unknown")
            current_tools = agent.get("tools", [])

            # Remove any existing skill functions from the tool list
            # (in case we're reloading and functions have changed)
            cleaned_tools = []
            for tool in current_tools:
                # Keep tool if it's not a skill function (doesn't contain skill pattern like "skill_name_function")
                is_skill_function = any(
                    f"{skill_name}_" in tool for skill_name in skill_function_map.keys()
                )
                if not is_skill_function:
                    cleaned_tools.append(tool)

            # Add current skill functions
            updated_tools = cleaned_tools + all_skill_functions

            # Update agent configuration if there are changes
            if set(current_tools) != set(updated_tools):
                agent["tools"] = updated_tools
                modified_agents.append(agent_name)

        # Write back to file if any changes were made
        if modified_agents:
            with open(agents_yaml_file, "w") as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)

            return {
                "success": True,
                "message": f"Updated agents.yaml with skill functions for agents: {', '.join(modified_agents)}",
                "modified_agents": modified_agents,
                "skill_functions_added": all_skill_functions,
            }
        else:
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

        # Load the current configuration
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

            # Check if this is a dedicated skill agent (agent name matches skill name)
            if agent_name == skill_name:
                agents_to_remove.append(i)
                changes_made.append(f"Removed dedicated agent '{agent_name}'")
                continue

            # Remove skill from tools list if present
            if "tools" in agent and isinstance(agent["tools"], list):
                original_tools = agent["tools"][:]
                # Remove exact skill name matches
                agent["tools"] = [tool for tool in agent["tools"] if tool != skill_name]
                # Also remove any tools that start with skill_name_ (skill functions)
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

        # Write back to file if changes were made
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
        if confirmation.strip().lower() != "yes":
            return {
                "success": False,
                "message": f"Deletion cancelled. To confirm deletion of skill '{skill_name}', you must type exactly 'yes' (case insensitive).",
                "required_confirmation": "yes",
            }

        skills_dir = Path(skills_path)
        skill_directory_path = skills_dir / skill_name

        # Check if skill directory exists
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

        # Get list of files that will be deleted (for confirmation message)
        files_to_delete = []
        for item in skill_directory_path.rglob("*"):
            if item.is_file():
                files_to_delete.append(str(item.relative_to(skill_directory_path)))

        # Perform the deletion
        import shutil

        shutil.rmtree(skill_directory_path)

        # Clean up references in agents.yaml file
        yaml_cleanup_result = remove_skill_from_agents_yaml(skill_name, "./agents.yaml")

        # Notify all toolboxes that a skill was removed
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

        # Prepare comprehensive result message
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


def register_skill_management_tools(toolbox):
    """Register skill management tools with the provided toolbox"""

    @toolbox.tool
    def create_skill(path: str, skill_name: str) -> dict:
        """Create a new skill directory structure with template files.

        IMPORTANT: Use relative path like './agent/skills' or '.' (current directory).
        The function will automatically ensure proper nesting to prevent duplicate
        directory structures. Skills will always be created at the correct
        ./agent/skills/{skill_name} level regardless of input path variations.

        Args:
            path: Base path - use '.' for current directory or './agent/skills'
            skill_name: Name of the skill (will be the directory name)
        """
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

                # Check for main.py
                main_py = skill_dir / "main.py"
                skill_info["has_main_py"] = main_py.exists()

                # Check for README.md
                readme = skill_dir / "README.md"
                skill_info["has_readme"] = readme.exists()

                # Count files
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

        ⚠️  WARNING: This action cannot be undone!

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
    def cleanup_agents_yaml(skill_name: str, confirmation: str) -> dict:
        """
        Remove orphaned skill references from agents.yaml without deleting skill files.

        Useful for cleaning up references to skills that were manually deleted.

        Args:
            skill_name: Name of the skill to remove from agents.yaml
            confirmation: Type exactly 'yes' to confirm cleanup

        Returns:
            Success/failure status and details of what was cleaned up

        Example:
            cleanup_agents_yaml("orphaned_skill", "yes")
        """
        if confirmation.strip().lower() != "yes":
            return {
                "success": False,
                "message": f"Cleanup cancelled. To confirm cleanup of '{skill_name}' references, you must type exactly 'yes'.",
                "required_confirmation": "yes",
            }

        return remove_skill_from_agents_yaml(skill_name, "./agents.yaml")

    @toolbox.tool
    async def execute_code_in_sandbox(
        skill_name: str,
        code: str,
        language: str = "python",
        libraries: list = None,
        timeout: float = 30,
    ) -> dict:
        """
        Execute code in a persistent, preloaded sandbox environment for a skill.

        This provides secure code execution with:
        - Isolated container environment
        - Preloaded common libraries
        - Persistent environments (no container startup delay)
        - Support for multiple languages (python, javascript, java, cpp, go)
        - Automatic plot/visualization capture
        - Resource limits and timeouts

        Args:
            skill_name: Name of the skill (for environment isolation)
            code: Code to execute
            language: Programming language ("python", "javascript", "java", "cpp", "go")
            libraries: Additional libraries to install (beyond preloaded ones)
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with execution results including stdout, stderr, plots, etc.

        Example:
            execute_code_in_sandbox("data_analyzer", "import pandas as pd\\nprint(pd.__version__)")
        """
        return await execute_skill_code(
            skill_name, code, language, libraries or [], timeout
        )

    @toolbox.tool
    async def get_sandbox_environment_info(skill_name: str) -> dict:
        """
        Get information about a skill's sandbox environment.

        Shows environment statistics including:
        - Environment age and usage
        - Preloaded libraries
        - Execution count
        - Resource usage

        Args:
            skill_name: Name of the skill

        Returns:
            Dictionary with environment information or None if no environment exists

        Example:
            get_sandbox_environment_info("data_processor")
        """
        info = await get_skill_environment_info(skill_name)
        if info:
            return {"success": True, "environment": info}
        else:
            return {
                "success": False,
                "message": f"No sandbox environment found for skill '{skill_name}'",
            }

    @toolbox.tool
    async def cleanup_sandbox_environment(
        skill_name: str, language: str = "python"
    ) -> dict:
        """
        Clean up a skill's sandbox environment to free resources.

        This will destroy the persistent environment and force creation
        of a fresh one on next use.

        Args:
            skill_name: Name of the skill
            language: Programming language of the environment

        Returns:
            Success/failure status

        Example:
            cleanup_sandbox_environment("data_processor")
        """
        success = await cleanup_skill_environment(skill_name, language)
        if success:
            return {
                "success": True,
                "message": f"Cleaned up sandbox environment for '{skill_name}'",
            }
        else:
            return {
                "success": False,
                "message": f"No sandbox environment found for skill '{skill_name}'",
            }

    @toolbox.tool
    def get_all_sandbox_stats() -> dict:
        """
        Get statistics for all active sandbox environments.

        Shows overview of all environments including:
        - Total number of environments
        - Per-environment statistics
        - Resource usage
        - Environment ages

        Returns:
            Dictionary with comprehensive sandbox statistics

        Example:
            get_all_sandbox_stats()
        """
        manager = get_sandbox_manager()
        stats = manager.get_environment_stats()
        return {"success": True, "stats": stats}

    @toolbox.tool
    def execute_skill_code_in_sandbox(
        skill_name: str,
        code: str,
        language: str = "python",
        libraries: list = None,
        timeout: float = 30,
    ) -> dict:
        """
        Execute skill code in a secure sandbox container (synchronous version).

        This is the primary tool for executing code from within skills. It provides:
        - Secure isolated execution environment
        - Support for multiple programming languages
        - Preloaded common libraries (numpy, pandas, requests, etc.)
        - Persistent environments for faster execution
        - Automatic plot/visualization capture
        - Resource limits and timeouts

        Languages supported:
        - python: Full Python environment with data science libraries
        - javascript: Node.js environment with common packages
        - java: OpenJDK with Maven support
        - cpp: GCC compiler with standard libraries
        - go: Go compiler and standard libraries

        Args:
            skill_name: Name of the skill (used for environment isolation)
            code: Code to execute in the sandbox
            language: Programming language ("python", "javascript", "java", "cpp", "go")
            libraries: Additional libraries to install (beyond preloaded ones)
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary containing:
            - success: Boolean indicating if execution succeeded
            - stdout: Standard output from code execution
            - stderr: Standard error output
            - plots: List of any generated plots/visualizations
            - execution_time: Time taken to execute
            - error: Error message if execution failed

        Example usage in skills:
            # Execute Python data analysis
            result = execute_skill_code_in_sandbox(
                skill_name="data_analyzer",
                code="import pandas as pd\\ndf = pd.DataFrame({'x': [1,2,3]})\\nprint(df.head())",
                language="python"
            )

            # Execute JavaScript
            result = execute_skill_code_in_sandbox(
                skill_name="web_processor",
                code="console.log('Hello from JavaScript')",
                language="javascript"
            )
        """
        import asyncio

        # Run the async function in the current event loop or create one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, we need to use a different approach
                import concurrent.futures

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
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(
                execute_skill_code(skill_name, code, language, libraries or [], timeout)
            )


# Convenience function for direct use in skills
def run_code_in_sandbox(
    skill_name: str,
    code: str,
    language: str = "python",
    libraries: list = None,
    timeout: float = 30,
) -> dict:
    """
    Convenience function for skills to execute code in sandbox.

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
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

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
