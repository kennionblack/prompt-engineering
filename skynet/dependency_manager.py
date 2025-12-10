"""
Dependency management for skills.
Handles checking and installing Python package dependencies.
"""

import subprocess
import sys
import importlib
import logging
from typing import List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def check_package_installed(package_name: str) -> bool:
    """
    Check if a Python package is installed and importable.

    Args:
        package_name (str): The package name to check (e.g., 'requests', 'beautifulsoup4')

    Returns:
        bool: True if package is installed and importable
    """
    # Handle package name vs import name mapping
    import_name_map = {
        "beautifulsoup4": "bs4",
        "pillow": "PIL",
        "scikit-learn": "sklearn",
        "python-dateutil": "dateutil",
    }

    import_name = import_name_map.get(package_name, package_name)

    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def install_package(package_name: str, version: Optional[str] = None) -> Tuple[bool, str]:
    """
    Install a Python package using pip.

    Args:
        package_name (str): The package name to install
        version (str, optional): Specific version to install (e.g., '2.31.0')

    Returns:
        Tuple[bool, str]: (success, output/error message)
    """
    try:
        package_spec = f"{package_name}=={version}" if version else package_name

        logger.info(f"Installing package: {package_spec}")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_spec],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"Successfully installed {package_spec}")
            return True, result.stdout
        else:
            logger.error(f"Failed to install {package_spec}: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        msg = f"Timeout installing {package_name}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Error installing {package_name}: {str(e)}"
        logger.error(msg)
        return False, msg


def parse_requirements(requirements_text: str) -> List[Tuple[str, Optional[str]]]:
    """
    Parse requirements.txt format text into (package, version) tuples.

    Args:
        requirements_text (str): Contents of requirements.txt

    Returns:
        List[Tuple[str, Optional[str]]]: List of (package_name, version) tuples
    """
    requirements = []
    for line in requirements_text.strip().split("\n"):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Handle version specifiers
        if "==" in line:
            package, version = line.split("==", 1)
            requirements.append((package.strip(), version.strip()))
        elif ">=" in line or "<=" in line or ">" in line or "<" in line:
            # For now, install latest if version constraints present
            package = line.split(">")[0].split("<")[0].split("=")[0].strip()
            requirements.append((package, None))
        else:
            requirements.append((line, None))

    return requirements


def check_skill_dependencies(skill_path: Path) -> Tuple[List[str], List[str]]:
    """
    Check which dependencies are missing for a skill.

    Args:
        skill_path (Path): Path to skill directory

    Returns:
        Tuple[List[str], List[str]]: (missing_packages, installed_packages)
    """
    requirements_file = skill_path / "requirements.txt"

    if not requirements_file.exists():
        return [], []

    requirements_text = requirements_file.read_text()
    requirements = parse_requirements(requirements_text)

    missing = []
    installed = []

    for package, version in requirements:
        if check_package_installed(package):
            installed.append(package)
        else:
            missing.append(package if not version else f"{package}=={version}")

    return missing, installed


def install_skill_dependencies(
    skill_path: Path, auto_confirm: bool = False
) -> Tuple[bool, str]:
    """
    Install missing dependencies for a skill.

    Args:
        skill_path (Path): Path to skill directory
        auto_confirm (bool): If False, requires user confirmation before installing

    Returns:
        Tuple[bool, str]: (success, message)
    """
    missing, installed = check_skill_dependencies(skill_path)

    if not missing:
        return True, f"All dependencies satisfied ({len(installed)} packages installed)"

    if not auto_confirm:
        return (
            False,
            f"Missing dependencies: {', '.join(missing)}. Use auto_confirm=True to install.",
        )

    # Install missing packages
    failed = []
    succeeded = []

    for package_spec in missing:
        if "==" in package_spec:
            package, version = package_spec.split("==", 1)
            success, msg = install_package(package, version)
        else:
            success, msg = install_package(package_spec)

        if success:
            succeeded.append(package_spec)
        else:
            failed.append((package_spec, msg))

    if failed:
        failure_msg = "; ".join([f"{pkg}: {msg}" for pkg, msg in failed])
        return False, f"Installed {len(succeeded)}/{len(missing)}. Failed: {failure_msg}"

    return (
        True,
        f"Successfully installed {len(succeeded)} packages: {', '.join(succeeded)}",
    )


def get_dependency_info(skill_path: Path) -> dict:
    """
    Get comprehensive dependency information for a skill.

    Args:
        skill_path (Path): Path to skill directory

    Returns:
        dict: {
            'has_requirements': bool,
            'total': int,
            'installed': List[str],
            'missing': List[str],
            'ready': bool
        }
    """
    requirements_file = skill_path / "requirements.txt"

    if not requirements_file.exists():
        return {
            "has_requirements": False,
            "total": 0,
            "installed": [],
            "missing": [],
            "ready": True,
        }

    missing, installed = check_skill_dependencies(skill_path)

    return {
        "has_requirements": True,
        "total": len(installed) + len(missing),
        "installed": installed,
        "missing": missing,
        "ready": len(missing) == 0,
    }
