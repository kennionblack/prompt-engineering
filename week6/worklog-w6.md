# Week 6: Multi-Agent Systems

## Executive Summary

This week was mostly spent learning about how multi-agent coordination patterns work. I also spent some time getting the Cloudflare MCP model up and running (admittedly without their integrated API approach).

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date     | Time | Description                                                                                                                                           |
| -------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10/13/25 | 1h   | Attended lecture                                                                                                                                      |
| 10/15/25 | 1.5h | Try to get Cloudflare MCP working, fail miserably                                                                                                     |
| 10/15/25 | 1h   | Attended lecture                                                                                                                                      |
| 10/16/25 | 1.5h | Get image processing deep learning [tutorial](https://pyimagesearch.com/2018/02/05/deep-learning-production-keras-redis-flask-apache/) up and running |
| 10/17/25 | 1h   | Read up on multi-agent coordination patterns<br>Watch [video](https://www.youtube.com/watch?v=2MYzc79Lj04) on OpenAI multi agent coordination         |
| 10/18/25 | 1h   | Fix the cloudflare-mcp bot                                                                                                                            |

## Class notes

- Multi-agent systems: using more than one agent in the execution of a workflow
- Coordination patterns
  - Supervisor
    - One agent delegates taks to specialized agents and integrates their work
    - Manager becomes the bottleneck because it has to process everyone else's input
  - Pipeline
    - Work flows through ordered stages that transforms the results
    - Relatively deterministic, easy to test
    - Early errors propagate (not necessarily error checking)
  - Planner-executor
    - Planner decomposes a complex task into subtask, executors are specialized for each task and perform them
    - Improves reasoning and shrinks context for sub-agents, which generally improves accuracy
    - Planners can propose infeasible goals
  - Generator-critic
    - One agent produces output, another evaluates it
    - Allows for iterative refinement loop
    - Critic must be fine-tuned
  - Committee
    - Multiple agents with different prompts solve the same problem, a judge merges results
    - Redundancy breeds reliability, but at a high cost
  - Tool Router
    - Central router decides which tool/API handles a request
    - Keeps tool management simple and scalable
    - Router needs to know how to call tools effectively

## Exercises

My main project this week was to try and get the Cloudflare MCP server up and running in preparation for the class demo, but that ultimately didn't work out. I did manage to hook up a Yahoo finance MCP server to my Cloudflare MCP client later in the week and deploy to Cloudflare.

I also spent some time getting an image processing deep learning model up and running. With a little more work, it would be relatively easy to feed the model processing results into an LLM client that could provide a natural language interface to describe image characteristics.

Code is [here](https://github.com/kennionblack/prompt-engineering/tree/main/week6/cloudflare-mcp).

## Findings

Most of my experience with building AI models is in Python, so using Typescript for Cloudflare's model was more of a stretch than I expected. Cloudflare uses a lot of configuration options that I did not know about, so I needed to lean on Copilot more than expected to get anything to deploy.

Most of the issues I had with the image processing were related to concurrency and server load as compared to getting the actual image processing working. In retrospect, I'd probably start with a simpler tutorial.
