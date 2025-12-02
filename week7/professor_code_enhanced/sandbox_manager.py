"""
Sandbox manager for professor_code_enhanced skills

Provides persistent, preloaded sandbox environments for skill execution.
"""

import asyncio
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
import time


class PersistentSandboxManager:
    """
    Manages persistent sandbox environments for skills.

    Features:
    - Preloaded environments with common libraries
    - Environment pooling to avoid container startup delays
    - Per-skill environment isolation
    - Automatic cleanup and recycling
    """

    def __init__(self, max_environments: int = 5, environment_ttl: int = 3600):
        self.max_environments = max_environments
        self.environment_ttl = environment_ttl  # 1 hour default
        self.environments = {}  # skill_name -> environment_info
        self._environment_lock = asyncio.Lock()

    async def get_or_create_environment(
        self,
        skill_name: str,
        language: str = "python",
        preload_libraries: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Get or create a persistent environment for a skill.

        Args:
            skill_name: Name of the skill
            language: Programming language (python, javascript, etc.)
            preload_libraries: Libraries to preload in the environment

        Returns:
            Environment info dictionary
        """
        async with self._environment_lock:
            env_key = f"{skill_name}_{language}"

            # Check if we have a valid environment
            if env_key in self.environments:
                env_info = self.environments[env_key]
                if time.time() - env_info["created_at"] < self.environment_ttl:
                    print(f"🔄 Reusing persistent environment for {skill_name}")
                    return env_info
                else:
                    # Environment expired, clean it up
                    await self._cleanup_environment(env_key)

            # Create new environment
            print(f"🚀 Creating new persistent environment for {skill_name}")
            env_info = await self._create_environment(
                skill_name, language, preload_libraries
            )

            # Cleanup old environments if we're at the limit
            if len(self.environments) >= self.max_environments:
                await self._cleanup_oldest_environment()

            self.environments[env_key] = env_info
            return env_info

    async def _create_environment(
        self, skill_name: str, language: str, libraries: List[str] = None
    ) -> Dict[str, Any]:
        """Create and preload a new environment."""
        try:
            from llm_sandbox import ArtifactSandboxSession

            # Standard libraries for different languages
            standard_libraries = {
                "python": ["requests", "json", "pathlib", "datetime", "os", "sys"],
                "javascript": ["axios", "lodash", "moment"],
                "java": [],
                "cpp": [],
                "go": [],
            }

            # Combine standard and requested libraries
            all_libraries = list(
                set(standard_libraries.get(language, []) + (libraries or []))
            )

            # Create session (this will create the container)
            session = ArtifactSandboxSession(
                lang=language,
                verbose=False,
                enable_plotting=language in {"python", "r"},
                keep_template=True,  # Keep container alive
            )

            # Open the session
            session.open()

            # Separate standard library from third-party libraries
            stdlib = {"json", "pathlib", "datetime", "os", "sys", "time", "traceback"}
            third_party_libs = [lib for lib in all_libraries if lib not in stdlib]
            stdlib_libs = [lib for lib in all_libraries if lib in stdlib]

            # Install third-party libraries first (without trying to import yet)
            if third_party_libs:
                print(
                    f"📦 Installing third-party libraries: {', '.join(third_party_libs)}"
                )
                # Just run a simple command with libraries parameter to trigger installation
                install_result = session.run(
                    code="print('Installation complete')",
                    libraries=third_party_libs,
                    timeout=120,  # Longer timeout for installation
                )
                if install_result.exit_code != 0:
                    print(f"⚠️  Warning: Installation issues: {install_result.stderr}")

            # Now preload/import all libraries (they should be installed by now)
            if all_libraries:
                preload_code = self._get_preload_code(language, all_libraries)
                if preload_code:
                    print(f"📦 Importing libraries: {', '.join(all_libraries)}")
                    result = session.run(
                        code=preload_code,
                        libraries=[],
                        timeout=60,  # Empty libraries list since already installed
                    )
                    if result.exit_code != 0:
                        print(f"⚠️  Warning: Some library imports failed: {result.stderr}")

            return {
                "session": session,
                "skill_name": skill_name,
                "language": language,
                "preloaded_libraries": all_libraries,
                "created_at": time.time(),
                "last_used": time.time(),
                "execution_count": 0,
            }

        except Exception as e:
            print(f"❌ Failed to create environment for {skill_name}: {e}")
            raise

    def _get_preload_code(self, language: str, libraries: List[str]) -> str:
        """Generate code to preload libraries."""
        if language == "python":
            # Import common libraries to ensure they're loaded
            imports = []
            for lib in libraries:
                if lib in ["requests", "json", "pathlib", "datetime", "os", "sys"]:
                    imports.append(f"import {lib}")
                elif lib in ["numpy", "pandas", "matplotlib", "seaborn"]:
                    imports.append(f"import {lib}")

            if imports:
                return "\n".join(imports) + "\nprint('Libraries preloaded successfully')"

        elif language == "javascript":
            # For Node.js, we'll require common modules
            requires = []
            for lib in libraries:
                if lib in ["axios", "lodash", "moment"]:
                    requires.append(f"const {lib} = require('{lib}');")

            if requires:
                return (
                    "\n".join(requires)
                    + "\nconsole.log('Libraries preloaded successfully');"
                )

        return ""

    async def execute_in_environment(
        self,
        skill_name: str,
        code: str,
        language: str = "python",
        libraries: List[str] = None,
        timeout: float = 30,
    ) -> Dict[str, Any]:
        """
        Execute code in a persistent environment.

        Args:
            skill_name: Name of the skill
            code: Code to execute
            language: Programming language
            libraries: Additional libraries to install
            timeout: Execution timeout

        Returns:
            Execution results dictionary
        """
        try:
            # Get or create environment
            env_info = await self.get_or_create_environment(
                skill_name, language, libraries
            )
            session = env_info["session"]

            print(f"🔧 Executing code for {skill_name} in persistent environment")
            print(f"📦 Preloaded libraries: {', '.join(env_info['preloaded_libraries'])}")
            if libraries:
                print(f"📦 Additional libraries: {', '.join(libraries)}")

            # Execute code
            result = session.run(code=code, libraries=libraries or [], timeout=timeout)

            # Update usage stats
            env_info["last_used"] = time.time()
            env_info["execution_count"] += 1

            # Process results
            output = {
                "success": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "plots": [],
                "language": language,
                "skill_name": skill_name,
                "environment_reused": True,
                "execution_count": env_info["execution_count"],
                "libraries_used": (env_info["preloaded_libraries"] + (libraries or [])),
            }

            # Note: Plot handling removed - not using plots directory

            print(
                f"✅ Execution complete (#{env_info['execution_count']} in this environment)"
            )
            return output

        except Exception as e:
            print(f"❌ Execution failed for {skill_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution failed: {str(e)}",
                "skill_name": skill_name,
                "environment_reused": False,
            }

    async def _cleanup_environment(self, env_key: str):
        """Clean up a specific environment."""
        if env_key in self.environments:
            env_info = self.environments[env_key]
            try:
                # Close the session (this should cleanup the container)
                if "session" in env_info:
                    env_info["session"].close()
                    print(f"🧹 Cleaned up environment: {env_key}")
            except Exception as e:
                print(f"⚠️  Warning: Error cleaning up environment {env_key}: {e}")
            finally:
                del self.environments[env_key]

    async def _cleanup_oldest_environment(self):
        """Clean up the oldest environment to make room for a new one."""
        if not self.environments:
            return

        # Find oldest environment
        oldest_key = min(
            self.environments.keys(), key=lambda k: self.environments[k]["created_at"]
        )
        await self._cleanup_environment(oldest_key)

    async def cleanup_all(self):
        """Clean up all environments."""
        env_keys = list(self.environments.keys())
        for env_key in env_keys:
            await self._cleanup_environment(env_key)
        print("🧹 All sandbox environments cleaned up")

    def get_environment_stats(self) -> Dict[str, Any]:
        """Get statistics about current environments."""
        stats = {
            "total_environments": len(self.environments),
            "max_environments": self.max_environments,
            "environments": {},
        }

        for env_key, env_info in self.environments.items():
            stats["environments"][env_key] = {
                "skill_name": env_info["skill_name"],
                "language": env_info["language"],
                "created_at": env_info["created_at"],
                "last_used": env_info["last_used"],
                "execution_count": env_info["execution_count"],
                "age_seconds": time.time() - env_info["created_at"],
                "idle_seconds": time.time() - env_info["last_used"],
                "preloaded_libraries": env_info["preloaded_libraries"],
            }

        return stats


# Global sandbox manager instance
_sandbox_manager = None


def get_sandbox_manager() -> PersistentSandboxManager:
    """Get the global sandbox manager instance."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = PersistentSandboxManager()
    return _sandbox_manager


# Utility functions for skills to use
async def execute_skill_code(
    skill_name: str,
    code: str,
    language: str = "python",
    libraries: List[str] = None,
    timeout: float = 30,
) -> Dict[str, Any]:
    """
    Execute code in a persistent sandbox environment for a skill.

    This is the main function that skills should use for code execution.
    """
    manager = get_sandbox_manager()
    return await manager.execute_in_environment(
        skill_name, code, language, libraries, timeout
    )


async def get_skill_environment_info(skill_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a skill's sandbox environment."""
    manager = get_sandbox_manager()
    stats = manager.get_environment_stats()

    for env_key, env_stats in stats["environments"].items():
        if env_stats["skill_name"] == skill_name:
            return env_stats

    return None


async def cleanup_skill_environment(skill_name: str, language: str = "python") -> bool:
    """Clean up a specific skill's environment."""
    manager = get_sandbox_manager()
    env_key = f"{skill_name}_{language}"

    if env_key in manager.environments:
        await manager._cleanup_environment(env_key)
        return True
    return False
