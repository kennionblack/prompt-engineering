"""
Demo skill showing simple math and greeting functions
"""

# Import the skill_function decorator
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from skill_manager import skill_function


@skill_function
def demo_add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


@skill_function
def demo_greet(name: str) -> str:
    """Greet someone by name"""
    return f"Hello, {name}! This is from the demo skill."
