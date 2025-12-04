import inspect
import json
import ast
import asyncio
import concurrent.futures
from typing import Dict, Any, Callable, List

from sandbox_manager import execute_skill_code
from result_chunker import chunk_large_result

# Standard library modules that come preloaded in the sandbox
STDLIB_MODULES = {
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


def extract_module_imports(skill_func: Callable) -> list[str]:
    """
    Extract module-level import statements from a skill function's module.

    Args:
        skill_func: The function to extract imports from

    Returns:
        List of import statement strings
    """
    module_imports = []
    try:
        module = inspect.getmodule(skill_func)
        if module and hasattr(module, "__file__") and module.__file__:
            module_source = inspect.getsource(module)

            tree = ast.parse(module_source)
            for node in tree.body:
                if isinstance(node, ast.Import):
                    # This block handles the below kind of statements
                    # import module
                    # import module as alias
                    for alias in node.names:
                        if alias.asname:
                            module_imports.append(
                                f"import {alias.name} as {alias.asname}"
                            )
                        else:
                            module_imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    # This block handles the below kind of statements
                    # from module import name,
                    # from module import name as alias
                    module_name = node.module or ""
                    names = []
                    for alias in node.names:
                        if alias.asname:
                            names.append(f"{alias.name} as {alias.asname}")
                        else:
                            names.append(alias.name)
                    module_imports.append(f"from {module_name} import {', '.join(names)}")
    except Exception as e:
        print(f"Could not extract module imports for skill {skill_func.__name__}: {e}")

    return module_imports


def detect_libraries_from_imports(imports: list[str]) -> list[str]:
    """
    Detect third-party libraries from import statements by filtering out stdlib.

    Args:
        imports: List of import statement strings

    Returns:
        List of unique third-party library names
    """
    libraries = []
    for imp in imports:
        if imp.startswith("import "):
            # Extract base module name from "import module" or "import module as alias" statements
            lib = imp.split()[1].split(" as ")[0].split(".")[0]
            if lib not in STDLIB_MODULES:
                libraries.append(lib)
        elif imp.startswith("from ") and " import " in imp:
            # Extract base module from "from module import name" statements
            lib = imp.split("from ")[1].split(" import")[0].strip().split(".")[0]
            if lib and lib not in STDLIB_MODULES:
                libraries.append(lib)

    # Remove duplicates
    return list(set(libraries))


def build_sandbox_execution_script(
    skill_func: Callable,
    skill_name: str,
    skill_dir: str,
    module_imports: list[str],
    args: tuple,
    kwargs: dict,
) -> str:
    """
    Build wrapper Python script for executing a skill function in the sandbox.

    Args:
        skill_func: The function to execute
        skill_name: Name of the skill
        skill_dir: Path to skill directory
        module_imports: List of import statements to include
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function

    Returns:
        Complete Python script as a string
    """
    # Get function source code
    func_source = inspect.getsource(skill_func)

    # Filter out skill_manager imports as these are not present in the sandbox
    import_section = "\n".join(
        [
            imp
            for imp in module_imports
            if not imp.startswith("from skill_manager import")
            and not imp.startswith("import skill_manager")
        ]
    )

    # Build the complete execution script
    return f"""
import json
import sys
from pathlib import Path

SKILL_DIR = Path("{skill_dir}")
SKILL_NAME = "{skill_name}"

# Define stub decorators such that skill code with decorators can run in sandbox
# It's easier to have no-op decorators than modify the ast parsing
def skill_function(func):
    return func

def sandbox_skill_function(func):
    return func

# Module-level imports from skill file
{import_section}

# Function source code
{func_source}

args = {repr(list(args)) if args else "[]"}
kwargs = {repr(kwargs) if kwargs else "{{}}"}

try:
    # Execute the function
    result = {skill_func.__name__}(*args, **kwargs)
    
    # Make result JSON-serializable
    def make_serializable(obj):
        if isinstance(obj, bytes):
            import base64
            return {{"__type__": "bytes", "data": base64.b64encode(obj).decode('ascii')}}
        elif isinstance(obj, dict):
            return {{k: make_serializable(v) for k, v in obj.items()}}
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return str(obj)  # Convert objects to string representation
        return obj
    
    serializable_result = make_serializable(result)
    
    # Return the result as JSON
    output = {{
        "success": True,
        "result": serializable_result,
        "function": "{skill_func.__name__}",
        "skill": "{skill_name}"
    }}
    print("SANDBOX_RESULT:", json.dumps(output))

except Exception as e:
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


def parse_sandbox_result(sandbox_result: Dict[str, Any]) -> Any:
    """
    Parse the result from sandbox stdout into JSON.

    Args:
        sandbox_result: Raw result dict from sandbox execution

    Returns:
        Parsed result or error dict
    """
    if sandbox_result.get("success") and sandbox_result.get("stdout"):
        stdout_lines = sandbox_result["stdout"].split("\n")
        for line in stdout_lines:
            if line.startswith("SANDBOX_RESULT:"):
                try:
                    result_json = line.replace("SANDBOX_RESULT:", "").strip()
                    parsed_result = json.loads(result_json)

                    if parsed_result.get("success"):
                        result = parsed_result["result"]
                        # Apply intelligent chunking if result is too large
                        chunked_result = chunk_large_result(result)
                        return chunked_result
                    else:
                        print(f"❌ Sandbox execution error: {parsed_result.get('error')}")
                        return {
                            "success": False,
                            "error": parsed_result.get("error"),
                            "traceback": parsed_result.get("traceback"),
                        }
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse sandbox result: {e}")
    return {
        "success": False,
        "error": "Sandbox execution failed or produced no parseable output",
        "sandbox_details": sandbox_result,
    }


def execute_function_in_sandbox(
    skill_func: Callable, skill_name: str, skill_dir: str, *args, **kwargs
) -> Any:
    """
    Execute an entire skill function in a sandbox environment.

    This serializes the function call, executes it in the sandbox, and returns the result.
    Automatically extracts module-level imports from the skill file.

    Args:
        skill_func: Function to execute
        skill_name: Name of the skill
        skill_dir: Path to skill directory
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or error dict
    """
    try:
        inspect.getsource(skill_func)
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not extract function source: {e}",
            "message": "Function cannot be executed in sandbox without source code",
        }

    module_imports = extract_module_imports(skill_func)

    execution_script = build_sandbox_execution_script(
        skill_func, skill_name, skill_dir, module_imports, args, kwargs
    )

    libraries = detect_libraries_from_imports(module_imports)
    if libraries:
        print(f"Detected libraries for sandbox: {', '.join(libraries)}")

    # Execute in sandbox with detected libraries and async support
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    execute_skill_code(
                        skill_name, execution_script, "python", libraries, 60
                    ),
                )
                sandbox_result = future.result()
        else:
            sandbox_result = loop.run_until_complete(
                execute_skill_code(skill_name, execution_script, "python", libraries, 60)
            )
    except RuntimeError:
        sandbox_result = asyncio.run(
            execute_skill_code(skill_name, execution_script, "python", libraries, 60)
        )

    # Parse and return the result
    return parse_sandbox_result(sandbox_result)


def execute_skill_function_in_sandbox(
    skill_name: str, func_name: str, skill_dir: str, *args, **kwargs
) -> Any:
    """
    Execute a skill function in sandbox by reading source from file (no import needed).

    This is used when local imports fail but the skill should run in sandbox anyway.

    Args:
        skill_name: Name of the skill
        func_name: Name of the function to execute
        skill_dir: Path to skill directory
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or error dict
    """
    from pathlib import Path

    try:
        main_py = Path(skill_dir) / "main.py"
        if not main_py.exists():
            return {"success": False, "error": f"main.py not found in {skill_dir}"}

        source = main_py.read_text()

        # Parse to find all imports
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        # Build execution script that loads entire module then calls function
        args_str = ", ".join([repr(arg) for arg in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        call_args = ", ".join(filter(None, [args_str, kwargs_str]))

        execution_script = f"""
import json
import sys

# Load the entire skill module
{source}

# Call the requested function
try:
    result = {func_name}({call_args})
    print(json.dumps({{"success": True, "result": result}}))
except Exception as e:
    import traceback
    print(json.dumps({{"success": False, "error": str(e), "traceback": traceback.format_exc()}}))
"""

        libraries = detect_libraries_from_imports(imports)
        if libraries:
            print(f"Detected libraries for sandbox: {', '.join(libraries)}")

        # Execute in sandbox
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        execute_skill_code(
                            skill_name, execution_script, "python", libraries, 60
                        ),
                    )
                    sandbox_result = future.result()
            else:
                sandbox_result = loop.run_until_complete(
                    execute_skill_code(
                        skill_name, execution_script, "python", libraries, 60
                    )
                )
        except RuntimeError:
            sandbox_result = asyncio.run(
                execute_skill_code(skill_name, execution_script, "python", libraries, 60)
            )

        return parse_sandbox_result(sandbox_result)

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to execute {func_name} in sandbox: {str(e)}",
        }
