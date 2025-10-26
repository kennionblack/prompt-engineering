import asyncio
import json
import sys
from pathlib import Path

from openai import AsyncOpenAI

from config import Agent, load_config
from tools import ToolBox

from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tool_box = ToolBox()


@tool_box.tool
def talk_to_user(message: str) -> str:
    """Send a message to the user and get the user's response.

    This is the ONLY way to communicate with the user,
    so all information to and from the user will come through this function.
    """
    print()
    print("AI: ", message)
    return input("User: ")


@tool_box.tool
def plan(thoughts: str):
    """
    Plan out what you want to do over the next few interactions with the user.

    Write your thoughts and strategy here.

    For example, if you need to ask the user a series of questions,
    you can enumerate them here to make sure you cover them all.

    Or if you need to call a series of functions, list them here
    so you remember what you planned to do.
    """
    print()
    print("----- PLAN ------")
    print(thoughts)
    print("-----------------")


@tool_box.tool
def reason(thoughts: str):
    """
    Reason about the task at hand.

    Write your thoughts here.
    You can also record information here you need to keep track of,
    but don't need to send to the user.

    IMPORTANT: This information is NOT visible to the user.
    If you need to send information to the user, use a different function.
    """
    print()
    print("--- REASONING ---")
    print(thoughts)
    print("-----------------")
    return None


@tool_box.tool
def make_dir(path: str):
    """Create directories and any missing parent directories."""
    Path(path).mkdir(parents=True, exist_ok=True)


@tool_box.tool
def write_file(path: str, content: str):
    """Write content to a file."""
    Path(path).resolve().write_text(content)


@tool_box.tool
def read_file(path: str) -> str:
    """Read the contents of a file."""
    return Path(path).resolve().absolute().read_text()


@tool_box.tool
def execute_code_in_sandbox(
    code: str, language: str = "python", libraries: list[str] = None, timeout: float = 30
) -> dict:
    """
    Execute code in a secure sandbox environment using LLM Sandbox.

    This tool provides secure code execution with the following features:
    - Isolated container environment (no access to host system)
    - Support for multiple languages: python, javascript, java, cpp, go
    - Automatic library/package installation
    - Plot and visualization capture
    - Resource limits and timeouts
    - Network isolation for security

    Args:
        code: The code to execute
        language: Programming language ("python", "javascript", "java", "cpp", "go")
        libraries: List of libraries to install (e.g., ["numpy", "matplotlib"])
        timeout: Execution timeout in seconds

    Returns:
        Dictionary with execution results including stdout, stderr, exit_code, and plots
    """
    try:
        from llm_sandbox import ArtifactSandboxSession

        print(f"\n🔒 EXECUTING {language.upper()} CODE IN SECURE SANDBOX")
        print(f"📦 Libraries: {libraries or 'None'}")
        print(f"⏱️  Timeout: {timeout}s")
        print("🔗 Code:")
        print(code)
        print("=" * 50)

        # Only enable plotting for languages that support it
        plotting_supported_languages = {"python", "r"}
        enable_plotting = language.lower() in plotting_supported_languages

        with ArtifactSandboxSession(
            lang=language,
            verbose=False,
            enable_plotting=enable_plotting,
            # Security: containers are isolated and destroyed after use
            keep_template=False,
        ) as session:
            result = session.run(code=code, libraries=libraries or [], timeout=timeout)

            # Convert result to dictionary for JSON serialization
            output = {
                "success": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "plots": [],
                "language": language,
                "libraries_used": libraries or [],
            }

            # Handle plots if any were generated (only for plotting-supported languages)
            if enable_plotting and result.plots:
                import base64
                from pathlib import Path

                # Create plots directory if it doesn't exist
                plots_dir = Path("sandbox_plots")
                plots_dir.mkdir(exist_ok=True)

                for i, plot in enumerate(result.plots):
                    plot_filename = f"plot_{i+1}.{plot.format.value}"
                    plot_path = plots_dir / plot_filename

                    # Save plot to file
                    with open(plot_path, "wb") as f:
                        f.write(base64.b64decode(plot.content_base64))

                    output["plots"].append(
                        {
                            "filename": plot_filename,
                            "path": str(plot_path.absolute()),
                            "format": plot.format.value,
                            "size_bytes": len(base64.b64decode(plot.content_base64)),
                            "width": plot.width,
                            "height": plot.height,
                        }
                    )

            print(f"✅ EXECUTION COMPLETE")
            print(f"📊 Success: {output['success']}")
            if output["stdout"]:
                preview = (
                    output["stdout"][:200] + "..."
                    if len(output["stdout"]) > 200
                    else output["stdout"]
                )
                print(f"📝 Output: {preview}")
            if output["stderr"]:
                print(f"⚠️  Errors: {output['stderr']}")
            if output["plots"]:
                print(f"📈 Generated {len(output['plots'])} plots")
            print("=" * 50)

            return output

    except Exception as e:
        print(f"Sandbox execution failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Sandbox execution failed: {str(e)}",
        }


@tool_box.tool
def list_sandbox_languages() -> dict:
    """
    List all programming languages supported by LLM Sandbox.

    Returns information about each language including:
    - File extensions
    - Package managers
    - Plotting library support
    - Example usage
    """
    return {
        "supported_languages": {
            "python": {
                "description": "Python programming language",
                "file_extension": ".py",
                "package_manager": "pip",
                "supports_plotting": True,
                "plotting_libraries": ["matplotlib", "seaborn", "plotly", "bokeh"],
                "example_libraries": ["numpy", "pandas", "requests", "scikit-learn"],
                "example_code": 'print("Hello from Python!")',
                "note": "Full plotting support with automatic capture",
            },
            "javascript": {
                "description": "JavaScript/Node.js",
                "file_extension": ".js",
                "package_manager": "npm",
                "supports_plotting": False,
                "plotting_libraries": [],
                "example_libraries": ["axios", "lodash", "moment"],
                "example_code": 'console.log("Hello from JavaScript!");',
                "note": "Text output only, no plotting support",
            },
            "java": {
                "description": "Java programming language",
                "file_extension": ".java",
                "package_manager": "maven",
                "supports_plotting": False,
                "plotting_libraries": [],
                "example_libraries": [],
                "example_code": 'public class Main { public static void main(String[] args) { System.out.println("Hello from Java!"); } }',
            },
            "cpp": {
                "description": "C++ programming language",
                "file_extension": ".cpp",
                "package_manager": "system",
                "supports_plotting": False,
                "plotting_libraries": [],
                "example_libraries": ["libstdc++"],
                "example_code": '#include <iostream>\nint main() { std::cout << "Hello from C++!" << std::endl; return 0; }',
            },
            "go": {
                "description": "Go programming language",
                "file_extension": ".go",
                "package_manager": "go mod",
                "supports_plotting": False,
                "plotting_libraries": [],
                "example_libraries": ["github.com/spyzhov/ajson"],
                "example_code": 'package main\nimport "fmt"\nfunc main() { fmt.Println("Hello from Go!") }',
            },
        },
        "security_features": [
            "Isolated container environment",
            "No access to host file system",
            "Network isolation (no internet access)",
            "Resource limits (CPU, memory)",
            "Execution timeouts",
            "Automatic cleanup after execution",
        ],
        "artifact_support": {
            "plots": ["PNG", "SVG", "PDF formats"],
            "automatic_capture": "Matplotlib, Seaborn, Plotly, Bokeh (Python only)",
            "file_operations": "Copy files to/from sandbox",
        },
    }


def add_agent_tools(agents: dict[str, Agent], tool_box: ToolBox):
    for name, agent in agents.items():
        tool_box.add_agent_tool(agent, run_agent)


async def run_agent(agent: Agent, tool_box: ToolBox, message: str | None):
    print("")
    print(f"---- RUNNING {agent['name']} ----")
    if message:
        print(message)
        print("----------------------------------")

    history = [{"role": "system", "content": agent["prompt"]}]
    if message is not None:
        history.append({"role": "user", "content": message})

    tools = tool_box.get_tools(agent["tools"])

    while True:
        response = await client.responses.create(
            input=history,
            model="gpt-4o",  # Using gpt-4o since gpt-5 may not be available
            tools=tools,
            **agent.get("kwargs", {}),
        )

        history += response.output

        for item in response.output:
            if item.type == "function_call":
                print(f"---- {agent['name']} calling {item.name} ----")
                result = await tool_box.run_tool(item.name, **json.loads(item.arguments))

                history.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

            elif item.type == "message":
                return response.output_text

            elif item.type == "reasoning":
                print(f"---- {agent['name']} REASONED ----")

            else:
                print(item, file=sys.stderr)


def main(config_file: Path):
    config = load_config(config_file)
    agents = {agent["name"]: agent for agent in config["agents"]}
    add_agent_tools(agents, tool_box)
    main_agent = config["main"]
    asyncio.run(run_agent(agents[main_agent], tool_box, None))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
