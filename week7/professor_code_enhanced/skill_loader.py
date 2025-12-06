import importlib.util
import sys
import functools
import inspect
import ast
import logging
from pathlib import Path
from typing import Dict, Any, Set, List, Tuple, get_origin, get_type_hints

from skill_decorators import DEFAULT_SKILL_TIMEOUT, run_with_timeout
from skill_execution import execute_function_in_sandbox

_loaded_skills: Set[str] = set()

logger = logging.getLogger(__name__)


def _convert_json_to_python_types(func, kwargs: dict) -> dict:
    """
    Convert JSON-compatible arguments to Python types based on function signature.
    """
    try:
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        converted = {}

        for arg_name, arg_value in kwargs.items():
            if arg_name not in sig.parameters:
                converted[arg_name] = arg_value
                continue

            param = sig.parameters[arg_name]
            expected_type = type_hints.get(arg_name, param.annotation)

            if expected_type is inspect.Parameter.empty:
                converted[arg_name] = arg_value
                continue

            # Handle tuple conversion (JSON arrays -> Python tuples)
            origin = get_origin(expected_type)
            if origin is tuple or expected_type is tuple:
                if isinstance(arg_value, (list, tuple)):
                    converted[arg_name] = tuple(arg_value)
                elif arg_value == "" or arg_value == "null":
                    # Empty string or "null" string -> None
                    converted[arg_name] = None
                else:
                    converted[arg_name] = arg_value
            # Handle empty string -> None for optional types
            elif arg_value == "" or arg_value == "null":
                # Check if parameter has default or is Optional
                if param.default is not inspect.Parameter.empty:
                    converted[arg_name] = None
                else:
                    converted[arg_name] = arg_value
            else:
                converted[arg_name] = arg_value

        return converted
    except Exception as e:
        logger.warning(f"Failed to convert arguments for {func.__name__}: {e}")
        return kwargs


def extract_functions_from_ast(skill_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Extract function signatures from skill's main.py using AST (no imports).

    Returns:
        Dict mapping function names to their metadata (params, return_type, docstring, is_sandbox)
    """
    main_py = skill_path / "main.py"
    if not main_py.exists():
        return {}

    try:
        source = main_py.read_text()
        tree = ast.parse(source)

        functions = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Check for skill_function or sandbox_skill_function decorator
            is_skill_func = False
            is_sandbox = False

            for decorator in node.decorator_list:
                dec_name = None
                if isinstance(decorator, ast.Name):
                    dec_name = decorator.id
                elif isinstance(decorator, ast.Call) and isinstance(
                    decorator.func, ast.Name
                ):
                    dec_name = decorator.func.id

                if dec_name == "skill_function":
                    is_skill_func = True
                elif dec_name == "sandbox_skill_function":
                    is_skill_func = True
                    is_sandbox = True

            if not is_skill_func or node.name.startswith("_"):
                continue

            # Extract parameters with defaults
            params = []
            num_defaults = len(node.args.defaults)
            num_args = len(node.args.args)

            for i, arg in enumerate(node.args.args):
                param_name = arg.arg

                # Try to extract type annotation
                type_annotation = "Any"
                if arg.annotation:
                    try:
                        type_annotation = (
                            ast.unparse(arg.annotation)
                            if hasattr(ast, "unparse")
                            else "Any"
                        )
                    except:
                        type_annotation = "Any"

                # Check if this parameter has a default value
                # Defaults are aligned to the end of the args list
                default_index = i - (num_args - num_defaults)
                has_default = default_index >= 0

                param_info = {
                    "name": param_name,
                    "type": type_annotation,
                    "has_default": has_default,
                }

                params.append(param_info)

            # Extract return type
            return_type = "Any"
            if node.returns:
                try:
                    return_type = (
                        ast.unparse(node.returns) if hasattr(ast, "unparse") else "Any"
                    )
                except:
                    return_type = "Any"

            # Extract docstring
            docstring = ast.get_docstring(node) or ""

            functions[node.name] = {
                "params": params,
                "return_type": return_type,
                "docstring": docstring,
                "is_sandbox": is_sandbox,
            }

        return functions

    except Exception as e:
        logger.error(f"Failed to parse AST for {skill_path}: {e}")
        return {}


def validate_skill_code(skill_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate skill code for common issues before loading.

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    main_py = skill_path / "main.py"

    if not main_py.exists():
        return False, ["main.py not found"]

    try:
        source = main_py.read_text()
        tree = ast.parse(source)

        # Check for undefined names (like logger without import)
        imported_names = {"skill_function", "sandbox_skill_function"}
        defined_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname if alias.asname else alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname if alias.asname else alias.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined_names.add(node.id)

        # Check for logger usage without logging import
        if "logger" in source and "logging" not in imported_names:
            warnings.append("Uses 'logger' but doesn't import logging")

        # Check for consistent indentation (tabs vs spaces)
        lines = source.split("\n")
        has_tabs = any("\t" in line and line.strip() for line in lines)
        has_spaces = any(
            line.startswith("    ") or line.startswith("  ") for line in lines
        )
        if has_tabs and has_spaces:
            warnings.append("Mixed tabs and spaces detected")

        # Check if functions have docstrings with Args section
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_"):
                    continue  # Skip private functions
                # Skip decorator stub functions (skill_function, sandbox_skill_function)
                if node.name in ["skill_function", "sandbox_skill_function"]:
                    continue
                docstring = ast.get_docstring(node)
                if not docstring:
                    warnings.append(f"Function '{node.name}' has no docstring")
                elif "Args:" not in docstring and len(node.args.args) > 0:
                    # Has parameters but no Args section
                    warnings.append(
                        f"Function '{node.name}' has parameters but no 'Args:' section in docstring"
                    )

        # Don't block loading for documentation warnings - they're not critical
        return True, warnings

    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]
    except Exception as e:
        warnings.append(f"Validation error: {e}")
        return True, warnings  # Don't block loading for validation errors


def create_lazy_skill_wrapper(
    skill_name: str, func_name: str, skill_dir: Path, metadata: Dict[str, Any]
):
    """
    Create a lazy-loading wrapper that only imports the skill module when called.

    This avoids import errors during skill registration if dependencies aren't installed locally.
    For sandbox skills, the actual execution happens in a container with dependencies.

    Args:
        skill_name: Name of the skill
        func_name: Name of the function to wrap
        skill_dir: Path to skill directory
        metadata: Function metadata from AST (params, return_type, docstring, is_sandbox)

    Returns:
        Wrapped function that lazy-loads the actual skill function
    """
    is_sandbox = metadata.get("is_sandbox", False)
    docstring = metadata.get("docstring", "")

    def lazy_wrapper(*args, **kwargs):
        """Execute skill function with lazy module loading."""
        # Import module only when actually called
        module_name = f"skill_{skill_name}"
        main_py = skill_dir / "main.py"

        try:
            # Check if module already loaded
            if module_name in sys.modules:
                skill_module = sys.modules[module_name]
            else:
                # Load module for the first time
                spec = importlib.util.spec_from_file_location(module_name, main_py)
                if not spec or not spec.loader:
                    return {
                        "success": False,
                        "error": f"Could not load module spec for {skill_name}",
                    }

                skill_module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = skill_module

                module_load_failed = False
                try:
                    spec.loader.exec_module(skill_module)
                except ImportError as e:
                    # If it's a sandbox skill, this is OK - imports will work in container
                    if is_sandbox:
                        logger.info(
                            f"Cannot import {skill_name} locally (will run in sandbox): {e}"
                        )
                        module_load_failed = True
                    else:
                        return {
                            "success": False,
                            "error": f"Import error: {e}. Use install_skill_dependencies to install required packages.",
                        }

            # For sandbox skills with import errors, we can't get the function object
            # but we can still execute by reading the source and running in sandbox
            if is_sandbox and (
                not hasattr(skill_module, func_name)
                or "module_load_failed" in locals()
                and module_load_failed
            ):
                # Execute directly in sandbox without the function object
                from skill_execution import execute_skill_function_in_sandbox

                return run_with_timeout(
                    execute_skill_function_in_sandbox,
                    DEFAULT_SKILL_TIMEOUT,
                    skill_name,
                    func_name,
                    str(skill_dir),
                    *args,
                    **kwargs,
                )

            # Get the actual function
            if not hasattr(skill_module, func_name):
                return {
                    "success": False,
                    "error": f"Function {func_name} not found in {skill_name}",
                }

            skill_func = getattr(skill_module, func_name)

            # Inject skill context
            if hasattr(skill_func, "__globals__"):
                skill_func.__globals__["SKILL_DIR"] = skill_dir
                skill_func.__globals__["SKILL_NAME"] = skill_name

            timeout = getattr(skill_func, "timeout", DEFAULT_SKILL_TIMEOUT)

            # Convert JSON types to Python types based on function signature
            converted_kwargs = _convert_json_to_python_types(skill_func, kwargs)

            # Execute based on sandbox flag
            if is_sandbox or getattr(skill_func, "auto_sandbox", False):
                return run_with_timeout(
                    execute_function_in_sandbox,
                    timeout,
                    skill_func,
                    skill_name,
                    str(skill_dir),
                    *args,
                    **converted_kwargs,
                )
            else:
                return run_with_timeout(skill_func, timeout, *args, **converted_kwargs)

        except Exception as e:
            logger.error(f"Error executing {func_name} from {skill_name}: {e}")
            return {"success": False, "error": f"Execution error: {str(e)}"}

    # Set wrapper metadata
    wrapper_name = f"{skill_name}_{func_name}"
    lazy_wrapper.__name__ = wrapper_name
    lazy_wrapper.__doc__ = docstring

    # Create a signature from metadata
    try:
        from typing import Union, Optional, Any as AnyType

        # Build evaluation context with typing constructs
        eval_context = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "tuple": tuple,
            "set": set,
            "None": type(None),
            "Union": Union,
            "Optional": Optional,
            "Any": AnyType,
        }

        params = []
        for param in metadata.get("params", []):
            # Try to evaluate annotation string to get actual type
            annotation_str = param.get("type", "Any")
            annotation = inspect.Parameter.empty

            if annotation_str and annotation_str != "Any":
                try:
                    # Evaluate the annotation string (e.g., "dict | None" -> Union[dict, None])
                    annotation = eval(annotation_str, eval_context)
                except:
                    # If evaluation fails, leave as empty (more permissive schema)
                    annotation = inspect.Parameter.empty

            # Handle default values
            default = inspect.Parameter.empty
            if param.get("has_default", False):
                # Parameter has a default, mark it as optional in signature
                default = None  # We don't know the actual default value, but None is safe

            params.append(
                inspect.Parameter(
                    param["name"],
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                    default=default,
                )
            )

        return_annotation_str = metadata.get("return_type", "Any")
        return_annotation = inspect.Parameter.empty

        if return_annotation_str and return_annotation_str != "Any":
            try:
                return_annotation = eval(return_annotation_str, eval_context)
            except:
                return_annotation = inspect.Parameter.empty

        lazy_wrapper.__signature__ = inspect.Signature(
            params, return_annotation=return_annotation
        )
    except Exception as e:
        logger.warning(f"Could not create signature for {wrapper_name}: {e}")

    return lazy_wrapper


def create_skill_wrapper(skill_func, skill_dir_path: Path, skill_name_ref: str):
    """
    Create a wrapper that provides skill context and handles execution.

    This wrapper allows for lazy loading as context is injected only when called.
    Supports both normal and auto-sandbox execution modes.

    Args:
        skill_func: The original skill function
        skill_dir_path: Path to the skill directory
        skill_name_ref: Name of the skill

    Returns:
        Wrapped function with skill context injection
    """
    # Check if skill function should run in sandbox automatically
    auto_sandbox = getattr(skill_func, "auto_sandbox", False)

    @functools.wraps(skill_func)
    def skill_wrapper(*args, **kwargs):
        print(f"Executing skill function: {skill_func.__name__} from {skill_name_ref}")

        # Inject skill directory path into the function's context
        if hasattr(skill_func, "__globals__"):
            skill_func.__globals__["SKILL_DIR"] = skill_dir_path
            skill_func.__globals__["SKILL_NAME"] = skill_name_ref

        timeout = getattr(skill_func, "timeout", DEFAULT_SKILL_TIMEOUT)

        try:
            if auto_sandbox:
                return run_with_timeout(
                    execute_function_in_sandbox,
                    timeout,
                    skill_func,
                    skill_name_ref,
                    str(skill_dir_path),
                    *args,
                    **kwargs,
                )
            else:
                # Normal execution on local machine with timeout
                # This function may still perform its own sandboxing if desired
                return run_with_timeout(skill_func, timeout, *args, **kwargs)
        except TimeoutError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Skill function {skill_func.__name__} timed out after {timeout} seconds. Consider optimizing the function or increasing timeout.",
            }

    skill_wrapper.__name__ = f"{skill_name_ref}_{skill_func.__name__}"

    skill_wrapper.__signature__ = inspect.signature(skill_func)

    return skill_wrapper


def load_skill_functions(
    skill_name: str, skills_path: str = "./agent/skills", tool_box=None
) -> Dict[str, Any]:
    """
    Load and register functions from a specific skill directory.

    Only function signatures are loaded initially.
    Full skill context is lazy loaded on-demand when called.

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

        # Validate skill code before loading (AST-based, no imports)
        is_valid, warnings = validate_skill_code(skill_dir)
        if warnings:
            for warning in warnings:
                print(f"⚠️  Skill '{skill_name}': {warning}")
        if not is_valid:
            return {
                "success": False,
                "message": f"Skill validation failed: {'; '.join(warnings)}",
            }

        main_py = skill_dir / "main.py"
        if not main_py.exists():
            return {
                "success": False,
                "message": f"No main.py found in skill {skill_name}",
            }

        # Extract functions from AST without importing (avoids dependency issues)
        functions_metadata = extract_functions_from_ast(skill_dir)

        if not functions_metadata:
            return {
                "success": False,
                "message": f"No skill functions found in {skill_name}",
            }

        # Register each skill function as a tool
        functions_registered = []

        for func_name, metadata in functions_metadata.items():
            # Create lazy-loading wrapper that imports module only when called
            wrapped_function = create_lazy_skill_wrapper(
                skill_name, func_name, skill_dir, metadata
            )

            tool_box.tool(wrapped_function)

            functions_registered.append(
                {
                    "name": wrapped_function.__name__,
                    "original_name": func_name,
                    "doc": metadata["docstring"],
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
    skills_path: str = "./agent/skills", tool_box=None
) -> Dict[str, Any]:
    """
    Scan the skills directory and load all skill functions as tools.

    Only function signatures are loaded initially.
    Full skill context is lazy loaded on-demand when functions are called.

    Args:
        skills_path: Path to the skills directory
        tool_box: ToolBox instance to register functions with

    Returns:
        Dictionary with success status and list of loaded skill functions
    """
    # Import here to avoid circular dependency
    from skill_lifecycle import update_agents_yaml_with_skills

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

        current_skills = set()

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

                function_names = [func["name"] for func in result.get("functions", [])]
                skill_function_map[skill_dir.name] = function_names

                print(f"Loaded {function_count} functions from skill: {skill_dir.name}")
            else:
                print(f"Failed to load skill {skill_dir.name}: {result['message']}")

        yaml_update_result = {"success": True, "message": "No skills to update"}
        if skill_function_map:
            yaml_update_result = update_agents_yaml_with_skills(skill_function_map)
            if yaml_update_result["success"]:
                print(f"{yaml_update_result['message']}")
            else:
                print(f"Failed to update agents.yaml: {yaml_update_result['message']}")

        # global keyword ensures we modify the module-level _loaded_skills set
        # instead of a local variable in this function
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
