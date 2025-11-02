"""
Helper script for web_fetch skill demonstrating sandbox patterns
"""

from sandbox_manager import execute_skill_code

# Example sandbox usage patterns for reference

async def example_data_processing():
    """Example: Process data with pandas in sandbox"""
    code = """
import pandas as pd
import json

# Sample data
data = {"values": [1, 2, 3, 4, 5], "labels": ["A", "B", "C", "D", "E"]}
df = pd.DataFrame(data)

# Process
summary = {
    "mean": df["values"].mean(),
    "std": df["values"].std(),
    "total": df["values"].sum()
}

print(json.dumps(summary, indent=2))
"""
    
    return await execute_skill_code(
        skill_name="web_fetch",
        code=code,
        language="python",
        libraries=["pandas", "numpy"],
        timeout=60
    )

async def example_web_request():
    """Example: Make HTTP request in sandbox"""
    code = """
import requests
import json

response = requests.get("https://httpbin.org/json")
data = response.json()

result = {
    "status": response.status_code,
    "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
}

print(json.dumps(result, indent=2))
"""
    
    return await execute_skill_code(
        skill_name="web_fetch",
        code=code,
        language="python",
        timeout=30
    )

async def example_visualization():
    """Example: Create visualization in sandbox"""
    code = """
import matplotlib.pyplot as plt
import numpy as np

# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.title("Sample Sine Wave")
plt.xlabel("X values")
plt.ylabel("Y values")
plt.grid(True)
plt.show()  # This will be captured automatically

print("Visualization created successfully")
"""
    
    return await execute_skill_code(
        skill_name="web_fetch",
        code=code,
        language="python",
        libraries=["matplotlib", "numpy"],
        timeout=45
    )

async def example_javascript():
    """Example: Run JavaScript code in sandbox"""
    code = """
const data = [1, 2, 3, 4, 5];

// Process data
const result = {
    sum: data.reduce((a, b) => a + b, 0),
    average: data.reduce((a, b) => a + b, 0) / data.length,
    max: Math.max(...data),
    min: Math.min(...data)
};

console.log("JavaScript processing complete:");
console.log(JSON.stringify(result, null, 2));
"""
    
    return await execute_skill_code(
        skill_name="web_fetch",
        code=code,
        language="javascript",
        libraries=["lodash"],
        timeout=30
    )
