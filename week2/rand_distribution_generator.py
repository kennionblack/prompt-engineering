import asyncio
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
from openai import AsyncOpenAI
import matplotlib.pyplot as plt
from collections import Counter


load_dotenv()


async def generate_rand_array(client: AsyncOpenAI, history):
    nums = []
    for i in range(0, 100):
        response = await client.responses.create(input=history, model="chatgpt-4o-latest")
        # print(response)

        message_index = 1 if response.output[0].type == "reasoning" else 0
        num_string = response.output[message_index].content[0].text
        try:
            nums.append(int(num_string))
        except ValueError:
            print(f"Invalid input, model output {num_string}")
    return nums


def display_results(nums):
    print("In display function")

    count_dict = Counter(nums)

    bins = range(1, 102)

    plt.figure(figsize=(12, 6))
    plt.hist(nums, bins=bins, edgecolor="black", alpha=0.4, color="skyblue", label="All numbers")
    frequent_nums = [num for num, count in count_dict.items() if count > 2]

    if frequent_nums:
        for num, count in sorted([(n, c) for n, c in count_dict.items() if c > 2]):
            plt.text(num, count + 0.2, f"{count}", ha="center", fontsize=9, fontweight="bold")

    plt.title("Distribution of Generated Random Numbers")
    plt.xlabel("Number")
    plt.ylabel("Frequency")
    plt.xticks(range(1, 106, 5))
    plt.grid(axis="y", alpha=0.75)
    # plt.legend()

    output_path = "distribution.png"
    plt.savefig(output_path)
    print(f"Plot saved to {output_path}")

    if frequent_nums:
        print(f"Numbers appearing more than twice: {len(frequent_nums)} unique values")
        for num, count in sorted([(n, c) for n, c in count_dict.items() if c > 2]):
            print(f"Number {num} appears {count} times")


async def main(prompt_file: Path):
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = prompt_file.read_text()
    system = [{"role": "system", "content": prompt}]

    nums = await generate_rand_array(client, system)
    display_results(nums)


"""
Exercise: Learn how to get an AI to shut up (e.g. end a conversation naturally)
AI does not replicate random. Get some kind of distribution that should be random that AI generates 
Jailbreak a prompt (GPT 3.5 is susceptible) - fill context window consistently with gorbage until it has more context about what you want than its system prompt
"""

if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
