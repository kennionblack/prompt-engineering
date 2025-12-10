import inspect
import json
import ast
import asyncio
import concurrent.futures
from typing import Dict, Any, Callable
import importlib.metadata
import importlib.util

from sandbox_manager import execute_skill_code
from result_chunker import chunk_large_result


def validate_python_code(code: str, filepath: str = "<string>") -> Dict[str, Any]:
    """
    Validate Python code by attempting to compile it and checking for basic errors.
    This catches syntax errors, undefined names in function signatures, and import issues.

    Args:
        code: Python code string to validate
        filepath: Optional filepath for better error messages

    Returns:
        Dictionary with:
        - success (bool): Whether validation passed
        - errors (list): List of error messages if validation failed
        - warnings (list): List of warning messages
    """
    errors = []
    warnings = []

    # Step 1: Check for basic syntax with ast.parse
    try:
        tree = ast.parse(code, filename=filepath)
    except SyntaxError as e:
        return {"success": False, "errors": [f"Syntax error at line {e.lineno}: {e.msg}"]}
    except Exception as e:
        return {"success": False, "errors": [f"Parse error: {str(e)}"]}

    # Step 2: Try to compile the code
    try:
        compile(code, filename=filepath, mode="exec")
    except SyntaxError as e:
        errors.append(f"Compilation error at line {e.lineno}: {e.msg}")
    except Exception as e:
        errors.append(f"Compilation error: {str(e)}")

    # Step 3: Check for undefined names in function signatures
    # Collect all defined names (imports, constants, functions, classes)
    defined_names = set()

    # Add built-in names
    import builtins

    defined_names.update(dir(builtins))

    # Add system-provided decorators
    defined_names.update(
        ["skill_function", "sandbox_skill_function", "SKILL_DIR", "SKILL_NAME"]
    )

    # Track imports for decorator validation
    imported_modules = set()
    imports_from_skill_manager = set()

    # Walk AST to find all definitions and imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_names.add(name)
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "skill_manager":
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports_from_skill_manager.add(name)

            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_names.add(name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined_names.add(node.target.id)

    # Now check for undefined names in function signatures (defaults) and decorator usage
    has_skill_functions = False
    skill_decorator_functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if function has skill decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id in ["skill_function", "sandbox_skill_function"]:
                        has_skill_functions = True
                        skill_decorator_functions.append((node.name, decorator.id))

                        # Check if decorator is imported from skill_manager
                        if decorator.id not in imports_from_skill_manager:
                            # Check if it's defined locally (fallback pattern)
                            is_locally_defined = decorator.id in [
                                n.name
                                for n in ast.walk(tree)
                                if isinstance(n, ast.FunctionDef) and n != node
                            ]

                            if not is_locally_defined:
                                errors.append(
                                    f"Function '{node.name}' uses @{decorator.id} but it's not properly imported. "
                                    f"Add: from skill_manager import skill_function, sandbox_skill_function"
                                )
                    elif decorator.id not in defined_names:
                        warnings.append(
                            f"Decorator @{decorator.id} may not be defined or imported"
                        )

            # Check default argument values for undefined names
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                for subnode in ast.walk(default):
                    if isinstance(subnode, ast.Name):
                        if subnode.id not in defined_names:
                            errors.append(
                                f"Undefined name '{subnode.id}' used in default argument "
                                f"for function '{node.name}' at line {node.lineno}"
                            )

            # Check for missing type annotations on function parameters
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != "self":
                    warnings.append(
                        f"Parameter '{arg.arg}' in function '{node.name}' has no type annotation"
                    )

    # Check if skill has functions but wrong import
    if has_skill_functions:
        # Check for wrong import module
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "skill" in node.module.lower()
            ):
                if node.module != "skill_manager":
                    errors.append(
                        f"Incorrect import: 'from {node.module} import ...' should be 'from skill_manager import skill_function, sandbox_skill_function'"
                    )

    # Step 4: Check for docstrings on functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            if not docstring:
                warnings.append(f"Function '{node.name}' has no docstring")
            elif docstring and node.args.args:
                # Check if docstring has Args section for functions with parameters
                if (
                    "Args:" not in docstring
                    and len([arg for arg in node.args.args if arg.arg != "self"]) > 0
                ):
                    warnings.append(
                        f"Function '{node.name}' has parameters but no 'Args:' section in docstring"
                    )

    if errors:
        return {"success": False, "errors": errors, "warnings": warnings}

    return {"success": True, "errors": [], "warnings": warnings}


def _build_wrapper_script(
    skill_name: str,
    skill_dir: str,
    imports: list[str],
    func_source: str,
    func_name: str,
    args: tuple = (),
    kwargs: dict = None,
    include_execution: bool = True,
) -> str:
    """
    Build the sandbox wrapper script. Shared by validation and execution.

    Args:
        skill_name: Name of the skill
        skill_dir: Path to skill directory
        imports: List of import statement strings (only used if func_source is a single function)
        func_source: Source code - can be a single function or entire module
        func_name: Name of the function to execute
        args: Positional arguments (only used if include_execution=True)
        kwargs: Keyword arguments (only used if include_execution=True)
        include_execution: Whether to include execution logic (False for validation)

    Returns:
        Complete wrapper script as string
    """
    if kwargs is None:
        kwargs = {}

    # Check if func_source is entire module or single function
    # Parse to detect module-level imports vs function-internal imports
    is_full_module = False
    try:
        tree = ast.parse(func_source)
        module_level_imports = [
            node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        # Check for multiple function definitions at module level
        function_count = len(
            [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        )

        is_full_module = len(module_level_imports) > 0 or function_count > 1
    except:
        is_full_module = (
            func_source.count("def ") > 1
            or func_source.startswith('"""')
            or func_source.startswith("'''")
        )

    # Only use extracted imports if we have a single function
    # For full modules, imports are already in the source
    import_section = ""
    if not is_full_module and imports:
        import_section = "\n".join(
            [
                imp
                for imp in imports
                if not imp.startswith("from skill_manager import")
                and not imp.startswith("import skill_manager")
            ]
        )
        if import_section:
            import_section = (
                f"\n# Module-level imports from skill file\n{import_section}\n"
            )

    # Build execution section if needed
    execution_section = ""
    if include_execution:
        execution_section = f"""
args = {repr(list(args)) if args else "[]"}
kwargs = {repr(kwargs) if kwargs else "{{}}"}

try:
    # Execute the function
    result = {func_name}(*args, **kwargs)
    
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
        "function": "{func_name}",
        "skill": "{skill_name}"
    }}
    print("SANDBOX_RESULT:", json.dumps(output))

except Exception as e:
    import traceback
    error_output = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc(),
        "function": "{func_name}",
        "skill": "{skill_name}"
    }}
    print("SANDBOX_RESULT:", json.dumps(error_output))
"""

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
{import_section}
# Skill code (function or full module)
{func_source}
{execution_section}
"""


def validate_skill_code_with_wrapper(
    code: str, skill_name: str = "test_skill"
) -> Dict[str, Any]:
    """
    Validate skill code by building the sandbox wrapper and checking if it compiles.
    This catches issues that would occur when the skill runs in the sandbox.

    Args:
        code: Python skill code to validate (main.py content)
        skill_name: Name of the skill for wrapper generation

    Returns:
        Dictionary with:
        - success (bool): Whether validation passed
        - errors (list): List of error messages if validation failed
        - warnings (list): List of warning messages
    """
    errors = []
    warnings = []

    # First validate the base code
    base_validation = validate_python_code(code, f"{skill_name}/main.py")
    if not base_validation["success"]:
        return base_validation

    warnings.extend(base_validation["warnings"])

    # Build a mock sandbox wrapper to test compilation
    try:
        # Parse to extract imports and function name
        tree = ast.parse(code)
        imports = []
        func_name = "unknown"

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        imports.append(f"import {alias.name} as {alias.asname}")
                    else:
                        imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                names = []
                for alias in node.names:
                    if alias.asname:
                        names.append(f"{alias.name} as {alias.asname}")
                    else:
                        names.append(alias.name)
                imports.append(f"from {module_name} import {', '.join(names)}")
            elif isinstance(node, ast.FunctionDef):
                # Extract first function name for validation
                func_name = node.name

        # Build wrapper script using shared function (without execution logic)
        wrapper_script = _build_wrapper_script(
            skill_name=skill_name,
            skill_dir=f"/tmp/skills/{skill_name}",
            imports=imports,
            func_source=code,
            func_name=func_name,
            include_execution=False,
        )

        # Try to parse and compile the wrapper
        try:
            wrapper_tree = ast.parse(
                wrapper_script, filename=f"sandbox_wrapper_{skill_name}.py"
            )
        except SyntaxError as e:
            errors.append(f"Sandbox wrapper syntax error at line {e.lineno}: {e.msg}")
            return {"success": False, "errors": errors, "warnings": warnings}

        try:
            compile(
                wrapper_script, filename=f"sandbox_wrapper_{skill_name}.py", mode="exec"
            )
        except SyntaxError as e:
            errors.append(
                f"Sandbox wrapper compilation error at line {e.lineno}: {e.msg}"
            )
        except Exception as e:
            errors.append(f"Sandbox wrapper compilation error: {str(e)}")

    except Exception as e:
        errors.append(f"Error building sandbox wrapper: {str(e)}")

    if errors:
        return {"success": False, "errors": errors, "warnings": warnings}

    return {"success": True, "errors": [], "warnings": warnings}


# Standard library modules that come preloaded in the sandbox
STDLIB_MODULES = {
    "__future__",
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
        List of unique third-party library names (mapped to package names)
    """

    def get_package_name(module_name: str) -> str:
        """Get the PyPI package name for a module using importlib.metadata."""
        # Skip lookup for stdlib modules
        if module_name in STDLIB_MODULES:
            return module_name

        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                # Module not found locally, use the name as-is
                return module_name

            # Only do package lookup for non-stdlib modules
            try:
                # Check directly if there's a distribution with this exact name
                try:
                    dist = importlib.metadata.distribution(module_name)
                    return dist.metadata["Name"]
                except importlib.metadata.PackageNotFoundError:
                    pass

                # If that fails, fallback to module name matching package name
                return module_name
            except Exception:
                pass

            return module_name
        except Exception:
            return module_name

    libraries = []
    for imp in imports:
        if imp.startswith("import "):
            # Extract base module name from "import module" or "import module as alias" statements
            lib = imp.split()[1].split(" as ")[0].split(".")[0]
            if lib not in STDLIB_MODULES:
                package_name = get_package_name(lib)
                libraries.append(package_name)
        elif imp.startswith("from ") and " import " in imp:
            # Extract base module from "from module import name" statements
            lib = imp.split("from ")[1].split(" import")[0].strip().split(".")[0]
            if lib and lib not in STDLIB_MODULES:
                package_name = get_package_name(lib)
                libraries.append(package_name)

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
    module = inspect.getmodule(skill_func)
    if module and hasattr(module, "__file__") and module.__file__:
        try:
            module_source = inspect.getsource(module)
        except Exception:
            # Fallback to just the function if module source unavailable
            module_source = inspect.getsource(skill_func)
    else:
        module_source = inspect.getsource(skill_func)

    return _build_wrapper_script(
        skill_name=skill_name,
        skill_dir=skill_dir,
        imports=module_imports,
        func_source=module_source,
        func_name=skill_func.__name__,
        args=args,
        kwargs=kwargs,
        include_execution=True,
    )


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
                        print(f"Sandbox execution error: {parsed_result.get('error')}")
                        return {
                            "success": False,
                            "error": parsed_result.get("error"),
                            "traceback": parsed_result.get("traceback"),
                        }
                except json.JSONDecodeError as e:
                    print(f"Failed to parse sandbox result: {e}")
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
