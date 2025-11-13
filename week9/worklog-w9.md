# Week 9: Images

## Executive Summary

This week I worked on my self-learning chatbot again. I made a sequence diagram that illustrates the desired execution path for how this agent should work to help me flesh out my mental model. I also built an explicit tool to return control from one agent to another as I only expose some tools to some agents and subagents were not returning control.

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description                                                                                                                      |
| ------- | ---- | -------------------------------------------------------------------------------------------------------------------------------- |
| 10/3/25 | 1h   | Attended lecture                                                                                                                 |
| 10/4/25 | 2h   | Build sequence diagram                                                                                                           |
| 10/5/25 | 1h   | Attended lecture                                                                                                                 |
| 10/5/25 | 1.5h | Finished sequence diagram<br>Tried to see how well multimodal inputs worked within this framework, ultimately decided against it |
| 10/6/25 | 1.5h | Try to squash hallucination issue for once and for all, fail miserably<br>Get agent handoff working more smoothly                |

## Exercises

I decided to make a [sequence diagram](https://github.com/kennionblack/prompt-engineering/tree/main/week7/professor_code_enhanced/sequence_diagram.svg) for this project as a visualization tool for how I want different processes and agents to work concurrently. As part of this ideation, I introduced the idea of storing skill information in a cloud hosted database which would allow multiple users of this framework to load skills from other users. This also allows the setup for agents with this framework be (mostly) machine-agnostic as the framework only needs an API key and database connection credentials to run. I haven't implemented the database portion yet but believe that I will use Postgres/Supabase for simplicity.

I also was having issues with agent orchestration not effectively transferring between agents, so I wrote new tools to delegate a task to a subagent and indicate that a subagent's execution has completed. This isn't a perfect system as my subagents are still trying to act as other agents with user prompts (which means that some tools aren't available), but this system at least helps agents explicitly transfer control.
