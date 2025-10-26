# Week 7: Tool agents

## Executive Summary

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date     | Time | Description                                                                                                                                                                                                                                                                                                                                                                      |
| -------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10/20/25 | 1h   | Attended lecture                                                                                                                                                                                                                                                                                                                                                                 |
| 10/22/25 | 1h   | Attended lecture                                                                                                                                                                                                                                                                                                                                                                 |
| 10/23/25 | 2h   | Started ideating on what kind of project I want to build<br>Used ChatGPT [deep reasoning research suggestions](https://github.com/kennionblack/prompt-engineering/tree/main/week7/code_reasoning_bot/deep_reasoning_response.txt) to flesh out ideas<br>Preliminary research on existing sandbox tooling, decided on [LLM Sandbox](https://vndee.github.io/llm-sandbox/) for now |
| 10/24/25 | 2h   | Used class provided code structure to get an agent up and running that can execute arbitrary code in an LLM Sandbox container                                                                                                                                                                                                                                                    |
| 10/25/25 | 2.5h | Watched [brief video](https://www.youtube.com/watch?v=xckU9n9r8Rs) on parallelizing agents<br>Read up on the [BMAD method](https://github.com/bmad-code-org/BMAD-METHOD) for agentic workflows<br>Look into Claude skills                                                                                                                                                        |

## Class notes

- Agent structure
  - In a nutshell, an agent can be defined with an identifier, prompt, model, and tools
  - Agent reasoning is just a tool lol
  - Make a tool that determines when it wants to talk to the user instead of hardcoding an input loop
    - This allows the agent to call multiple tools as it goes before needing user input
    - This approach also opens up using an agent that can interface between multiple users
    - .yaml or .md files can be fed into an agentic framework to create completely separate model experiences
    - Subagents can be defined as tools in other agents for easy access

## Exercises

I wanted to try out the code in class with some of the ideas that I've been playing with, so I got an agent running that was able to execute code in a container with LLM Sandbox. This agent can be found in [this directory](https://github.com/kennionblack/prompt-engineering/tree/main/week6/cloudflare-mcp) The container is initialized and torn down for each code request, which makes execution times of even simple programs take upwards of a minute.

## Findings

Spinning up a new container and tearing it down across multiple code executions is probably more secure than having a long-lived code sandbox session inside a container, but it does make requests involving code execution super slow. I'm looking into ways to make sandbox environments as stateless as possible to alleviate some of these issues.

Anthropic has a new-ish idea of building [skills](https://www.anthropic.com/news/skills) for an agent that effectively store instructions for how to execute arbitrary tasks. This differs from a tool executing code in that a skill is basically a directory with a README that links resources, documentation, and even scripts for how to execute arbitrary tasks, while a tool call (in its simplest form) is simply invoking code external to the agent on the host machine. One of the advantages of these skill documents is that only a name and description string are provided to the agent, which helps keep the context window small. When needed, an agent can reference the skill directory for the needed skill and read more detailed context, but this is conditional on the user's request and is not loaded into memory each time. This context window management can similarly be an advantage over traditional MCP, which often loads an entire set of tools available via MCP (including function parameters) into the context window of an agent, which takes far more context space than a skill reference necessitates.

## Conclusions

One of the perks of LLM Sandbox is that it is capable of executing code in multiple different languages, which makes me wonder if there's some kind of benchmarking that can be done on language performance for certain tasks. Preliminary research indicates that Python is the language of choice for most LLM-generated code, but I can also imagine that websites are more natively built in JS, statistical analysis can be done equally as well in R as in Python, etc. This may be a project for another week to determine benchmarks for different languages, then compare performance (especially in these containers).
