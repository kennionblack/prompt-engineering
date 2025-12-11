## Skynet

I want to build an agentic system that is able to leverage the idea of skills from Anthropic to dynamically build its own skills that can execute code to complete a user task.

## Persistence

I want to use Postgres (probably within Supabase) to store information associated with each skill. This shouldn't need to be too complicated.

[ERD link](https://github.com/kennionblack/prompt-engineering/tree/main/skynet/initial_erd.md)

## Sequence diagram

In lieu of an architecture diagram, I built a sequence diagram that should help illustrate how I want this program to work. I don't know how I'm going to get all of these threads working yet but I hope to be able to have these services running together at the same time.

[Diagram link](https://github.com/kennionblack/prompt-engineering/tree/main/skynet/sequence_diagram.svg)

## Goals

I want to put a couple hours into this each week. There's about four weeks to complete this, so I've outlined what I want to accomplish each week.

Week 1: Figure out how to execute code within a sandbox, research agent orchestration strategies

Week 2: Build user interface agent system prompts and tools that allow the user interface to actuallly write code, make skill builder agent dedicated to writing skill code and storing specific knowledge

Week 3: Get database storage of skills working, figure out how to run different agents on different threads instead of synchronously

Week 4: User testing with a variety of different skills, build web interface for client with Gradio

Week 5: Finishing touches and prepare for presentation
