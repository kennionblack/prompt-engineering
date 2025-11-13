import inspect
import traceback
from pathlib import Path
from types import UnionType
from typing import Any, Callable, get_type_hints, Literal, get_origin, get_args, Union

from openai.types.responses import FunctionToolParam

from config import Agent

_tools: dict[str, Callable] = {}

# Observer pattern for toolbox registration and tool change notifications
_toolbox_observers = []
_tool_change_observers = []
_active_toolboxes = []  # Track all active toolboxes


def register_toolbox_observer(observer_func):
    """Register a function to be called when a toolbox is created"""
    _toolbox_observers.append(observer_func)


def register_tool_change_observer(observer_func):
    """Register a function to be called when tools are added/changed"""
    _tool_change_observers.append(observer_func)


def notify_toolbox_created(toolbox):
    """Notify all observers that a toolbox has been created"""
    _active_toolboxes.append(toolbox)
    for observer in _toolbox_observers:
        try:
            observer(toolbox)
        except Exception as e:
            print(f"Error notifying toolbox observer: {e}")


def notify_tool_change(event_type: str, tool_info: dict, source_toolbox=None):
    """Notify all observers that tools have changed"""
    for observer in _tool_change_observers:
        try:
            observer(event_type, tool_info, source_toolbox)
        except Exception as e:
            print(f"Error notifying tool change observer: {e}")


def broadcast_reload_to_all_toolboxes(source_toolbox=None):
    """Trigger reload across all active toolboxes"""
    for toolbox in _active_toolboxes:
        if toolbox != source_toolbox:  # Don't reload the source
            try:
                # Check if this toolbox has a reload capability
                if hasattr(toolbox, "reload_external_tools"):
                    toolbox.reload_external_tools()
            except Exception as e:
                print(f"Error during toolbox reload: {e}")


def _is_optional(annotation) -> bool:
    origin = get_origin(annotation)
    args = get_args(annotation)
    return (origin is UnionType or origin is Union) and type(None) in args


def _get_strict_json_schema_type(annotation) -> dict:
    """
    Convert Python type annotations to OpenAI JSON schema format.

    This is a robust fallback approach that handles complex types gracefully
    by using a priority system and fallbacks instead of raising errors.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle Optional types (Union[X, None])
    if _is_optional(annotation):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _get_strict_json_schema_type(non_none_args[0])
        elif len(non_none_args) > 1:
            # Multiple non-None types - use priority fallback
            return _resolve_union_with_priority(non_none_args)
        else:
            # Only None - treat as Any
            return {
                "type": "string",
                "description": "Any value (originally None-only Union)",
            }

    # Handle non-Optional Union types
    if origin is Union or origin is UnionType:
        return _resolve_union_with_priority(args)

    # Direct type mapping
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        tuple: "array",
    }

    # Handle direct type matches
    if annotation in type_map:
        return _get_schema_for_type(annotation, type_map)

    # Handle generic types (List[X], Dict[X, Y], etc.)
    if origin in type_map:
        return _get_schema_for_generic_type(origin, args, type_map)

    # Handle other specific cases
    if origin is Literal:
        return {"type": "string", "enum": list(args)}

    # Fallback for unknown types - be permissive
    print(f"⚠️  Unknown type annotation {annotation}, using string fallback")
    return {"type": "string", "description": f"Unknown type: {annotation}"}


def _resolve_union_with_priority(union_args) -> dict:
    """
    Resolve Union types using a priority system.

    Instead of failing on complex unions, we pick the most appropriate type
    based on priority and practical JSON schema compatibility.
    """
    # Filter out NoneType if present
    filtered_args = [arg for arg in union_args if arg is not type(None)]

    if not filtered_args:
        return {"type": "string", "description": "Empty union"}

    # Priority order: more specific to less specific
    type_priority = [
        # Basic JSON-compatible types (highest priority)
        str,
        int,
        float,
        bool,
        # Complex but handleable types
        list,
        dict,
        tuple,
        # Catch common patterns
        Any,
    ]

    # First, try to find a high-priority type
    for priority_type in type_priority:
        if priority_type in filtered_args:
            try:
                return _get_strict_json_schema_type(priority_type)
            except:
                continue

    # If no high-priority types, try the first argument
    for arg in filtered_args:
        try:
            return _get_strict_json_schema_type(arg)
        except:
            continue

    # Final fallback - string with description
    return {
        "type": "string",
        "description": f"Union type with args: {[str(arg) for arg in filtered_args]}",
    }


def _get_schema_for_type(annotation, type_map) -> dict:
    """Get schema for a direct type annotation."""
    if annotation is list:
        return {"type": "array", "items": {"type": "string"}}
    elif annotation is dict:
        return {"type": "object", "additionalProperties": False}
    elif annotation is tuple:
        return {"type": "array", "items": {"type": "string"}}
    return {"type": type_map[annotation]}


def _get_schema_for_generic_type(origin, args, type_map) -> dict:
    """Get schema for generic types like List[X], Dict[X, Y], etc."""
    if origin is list:
        if args:
            try:
                item_type = _get_strict_json_schema_type(args[0])
                return {"type": "array", "items": item_type}
            except:
                pass
        return {"type": "array", "items": {"type": "string"}}

    elif origin is dict:
        # For Dict types, we'll use object with additionalProperties
        return {"type": "object", "additionalProperties": False}

    elif origin is tuple:
        if args:
            try:
                # Use first arg type for all tuple elements
                item_type = _get_strict_json_schema_type(args[0])
                return {"type": "array", "items": item_type}
            except:
                pass
        return {"type": "array", "items": {"type": "string"}}

    # Fallback for unknown generic types
    return {"type": type_map.get(origin, "string")}


def generate_function_schema(func: Callable[..., Any]) -> FunctionToolParam:
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    params = {}
    required = []

    for name, param in sig.parameters.items():
        if name in {"self", "ctx"}:
            continue

        ann = type_hints.get(name, param.annotation)
        if ann is inspect._empty:
            raise TypeError(f"Missing type annotation for parameter: {name}")

        schema_entry = _get_strict_json_schema_type(ann)
        params[name] = schema_entry

        # Only add to required if parameter has no default value
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "name": func.__name__,
        "description": func.__doc__ or "",
        "parameters": {
            "type": "object",
            "properties": params,
            "required": required,
            "additionalProperties": False,
        },
    }


class ToolBox:
    _tools: list[FunctionToolParam]

    def __init__(self):
        self._funcs = {}
        self._tools = []
        self._reload_callbacks = []  # Functions to call when reloading
        # Notify observers that a toolbox has been created
        notify_toolbox_created(self)

    def tool(self, func):
        self._tools.append(generate_function_schema(func))

        if inspect.iscoroutinefunction(func):

            async def safe_func(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except:
                    return traceback.format_exc()

        else:

            def safe_func(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except:
                    return traceback.format_exc()

        self._funcs[func.__name__] = safe_func
        return func

    @property
    def tools(self):
        """Get dictionary of all registered tool names and functions"""
        return dict(self._funcs)

    def get_tools(self, tool_names: list[str]):
        return [tool for tool in self._tools if tool["name"] in set(tool_names)]

    async def run_tool(self, tool_name: str, **kwargs):
        tool = self._funcs.get(tool_name)
        
        # Check if this is a skill function that might need error recovery
        if hasattr(tool, 'is_skill_function') and tool.is_skill_function:
            return await self._run_skill_with_recovery(tool_name, tool, **kwargs)
        
        # Regular tool execution
        result = tool(**kwargs)
        if inspect.iscoroutine(result):
            return await result
        else:
            return result
    
    async def _run_skill_with_recovery(self, tool_name: str, tool_func, **kwargs):
        """Run a skill function with automatic error recovery and regeneration."""
        try:
            # First attempt - try to run the skill normally
            result = tool_func(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            
            # Test JSON serialization to catch serialization errors early
            import json
            json.dumps(result)  # This will raise TypeError if not serializable
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"🚨 Skill error in {tool_name}: {error_msg}")
            
            # Check if this is a serialization error or other common issues
            if self._should_attempt_recovery(error_msg):
                print(f"🔧 Attempting automatic skill recovery for {tool_name}...")
                return await self._attempt_skill_recovery(tool_name, error_msg, kwargs)
            else:
                # Re-raise the error if it's not something we can recover from
                raise
    
    def _should_attempt_recovery(self, error_msg: str) -> bool:
        """Determine if we should attempt automatic recovery for this error."""
        recoverable_errors = [
            "not JSON serializable",
            "Object of type bytes",
            "Object of type datetime",
            "Object of type Decimal",
            "cannot serialize",
            "unhashable type",
            "AttributeError",  # Common in skill functions
            "TypeError",       # Type-related issues
        ]
        
        return any(err in error_msg for err in recoverable_errors)
    
    async def _attempt_skill_recovery(self, tool_name: str, error_msg: str, original_kwargs: dict):
        """Attempt to recover from skill errors by regenerating the skill."""
        try:
            # Extract skill name from tool name (e.g., "web_fetch_fetch_url" -> "web_fetch")
            parts = tool_name.split('_')
            if len(parts) >= 2:
                skill_name = parts[0] + '_' + parts[1]  # e.g., "web_fetch"
            else:
                skill_name = parts[0]
            
            # Get the original skill file path
            skill_path = Path(f"./agent/skills/{skill_name}/main.py")
            if not skill_path.exists():
                print(f"❌ Cannot recover: skill file not found at {skill_path}")
                raise Exception(f"Original skill error: {error_msg}")
            
            # Read the current broken skill code
            with open(skill_path, 'r') as f:
                broken_code = f.read()
            
            # Create recovery prompt for LLM
            recovery_prompt = f"""The skill function '{tool_name}' encountered an error during execution:

ERROR: {error_msg}

BROKEN CODE:
```python
{broken_code}
```

FUNCTION CALL THAT FAILED:
Tool: {tool_name}
Arguments: {original_kwargs}

Please fix this skill code to:
1. Handle the specific error that occurred
2. Ensure all return values are JSON serializable (no bytes, datetime, or other non-serializable objects)
3. Convert bytes to base64 strings, datetime to ISO strings, etc.
4. Maintain the same function signature and behavior
5. Keep all existing imports and decorators

Return ONLY the corrected Python code for the main.py file, no explanations."""

            # Call the skill_builder agent to fix the skill
            from skill_manager import register_skill_management_tools
            temp_toolbox = ToolBox()
            register_skill_management_tools(temp_toolbox)
            
            # Attempt automatic fix by updating the skill file
            print(f"🤖 Applying automatic fix for {skill_name}...")
            
            # Apply common fixes based on error type
            fixed_code = self._apply_automatic_fixes(broken_code, error_msg)
            
            if fixed_code != broken_code:
                # Write the fixed code back
                with open(skill_path, 'w') as f:
                    f.write(fixed_code)
                
                print(f"✅ Applied automatic fix to {skill_path}")
                
                # Reload the skill
                from skill_manager import load_all_skill_functions
                load_all_skill_functions(self)
                
                # Retry the function call
                print(f"🔄 Retrying {tool_name} with fixed code...")
                new_tool = self._funcs.get(tool_name)
                if new_tool:
                    result = new_tool(**original_kwargs)
                    if inspect.iscoroutine(result):
                        result = await result
                    
                    # Test serialization again
                    import json
                    json.dumps(result)
                    
                    print(f"🎉 Recovery successful for {tool_name}!")
                    return result
            
            # If automatic fix didn't work, provide helpful error message
            return {
                "error": error_msg,
                "recovery_attempted": True,  
                "skill_name": skill_name,
                "message": f"Skill {tool_name} failed with error: {error_msg}. Automatic recovery was attempted but unsuccessful. Please check the skill code manually."
            }
            
        except Exception as recovery_error:
            print(f"❌ Recovery failed: {recovery_error}")
            # Return the original error
            raise Exception(f"Original error: {error_msg}. Recovery failed: {recovery_error}")
    
    def _apply_automatic_fixes(self, code: str, error_msg: str) -> str:
        """Apply common automatic fixes to skill code based on error patterns."""
        fixed_code = code
        
        # Fix 1: bytes serialization issues
        if "Object of type bytes" in error_msg or "not JSON serializable" in error_msg:
            # Replace direct content assignment with base64 encoding
            if "result['content'] = response.content" in fixed_code:
                fixed_code = fixed_code.replace(
                    "result['content'] = response.content",
                    "result['content_base64'] = base64.b64encode(response.content).decode('ascii')"
                )
                
                # Add base64 import if not present
                if "import base64" not in fixed_code:
                    lines = fixed_code.split('\n')
                    # Find where to insert import (after existing imports)
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('import ') or line.strip().startswith('from '):
                            insert_idx = i + 1
                        elif line.strip() and not line.strip().startswith('#'):
                            break
                    
                    lines.insert(insert_idx, "import base64")
                    fixed_code = '\n'.join(lines)
            
            # Fix other common bytes issues
            if "= response.content" in fixed_code and "base64" not in fixed_code:
                fixed_code = fixed_code.replace(
                    "= response.content",
                    "= base64.b64encode(response.content).decode('ascii')"
                )
        
        # Fix 2: datetime serialization issues  
        if "Object of type datetime" in error_msg:
            # Add datetime import and conversion
            if "from datetime import datetime" not in fixed_code:
                fixed_code = "from datetime import datetime\n" + fixed_code
            
            # Replace datetime objects with ISO strings
            if ".isoformat()" not in fixed_code:
                fixed_code = fixed_code.replace(
                    "datetime.now()",
                    "datetime.now().isoformat()"
                )
        
        # Fix 3: Return dict instead of complex objects
        if "unhashable type" in error_msg or "AttributeError" in error_msg:
            # Add a result sanitization function at the end
            if "@skill_function" in fixed_code and "def sanitize_result" not in fixed_code:
                fixed_code += """

def sanitize_result(obj):
    \"\"\"Convert complex objects to JSON-serializable format\"\"\"
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('ascii')
    elif isinstance(obj, dict):
        return {k: sanitize_result(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_result(item) for item in obj]
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool)):
        return str(obj)
    else:
        return obj

# Wrap the skill function result
original_result = result
result = sanitize_result(original_result)
"""
            
        return fixed_code

    def add_agent_tool(self, agent: Agent, run_agent):
        async def function(message: str) -> str:
            return await run_agent(agent, self, message, interactive=False)

        function.__name__ = agent["name"]
        function.__doc__ = agent["description"]

        self.tool(function)

    def register_reload_callback(self, callback_func):
        """Register a function to be called when this toolbox should reload external tools"""
        self._reload_callbacks.append(callback_func)

    def reload_external_tools(self):
        """Trigger reload of external tools (called by observer pattern)"""
        for callback in self._reload_callbacks:
            try:
                result = callback()
                print(f"🔄 Reloaded tools: {result.get('message', 'success')}")
            except Exception as e:
                print(f"Error during tool reload: {e}")

    def notify_tool_added(self, tool_name: str, tool_info: dict = None):
        """Notify other toolboxes that a new tool was added"""
        notify_tool_change(
            "tool_added",
            {
                "tool_name": tool_name,
                "tool_info": tool_info or {},
                "toolbox_id": id(self),
            },
            source_toolbox=self,
        )
