import inspect
import traceback
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
    origin = get_origin(annotation)
    args = get_args(annotation)

    if _is_optional(annotation):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _get_strict_json_schema_type(non_none_args[0])
        raise TypeError(f"Unsupported Union with multiple non-None values: {annotation}")

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    if annotation in type_map:
        if annotation is list:
            return {
                "type": "array",
                "items": {"type": "string"},
            }  # Default to string items
        return {"type": type_map[annotation]}

    if origin in type_map:
        if origin is list:
            return {
                "type": "array",
                "items": {"type": "string"},
            }  # Default to string items
        return {"type": type_map[origin]}

    if origin is Literal:
        values = args
        if all(isinstance(v, (str, int, bool)) for v in values):
            return {
                "type": "string" if all(isinstance(v, str) for v in values) else "number",
                "enum": list(values),
            }
        raise TypeError("Unsupported Literal values in annotation")

    raise TypeError(f"Unsupported parameter type: {annotation}")


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

        required.append(name)
        params[name] = schema_entry

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
        "strict": True,
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
        result = tool(**kwargs)
        if inspect.iscoroutine(result):
            return await result
        else:
            return result

    def add_agent_tool(self, agent: Agent, run_agent):
        async def function(message: str) -> str:
            return await run_agent(agent, self, message)

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
