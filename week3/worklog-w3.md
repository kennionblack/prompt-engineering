# Week 3: Calling all the tools

## Executive Summary

I wanted to build a full agentic workflow that scrapes a website, parses data into a MySQL database, then provides a natural language interface for a user to ask questions about the data. The workflow constructs a SQL query based on the user's question, then translates the query response into a human-readable answer to the user's question. Code can be found at [this link](https://github.com/kennionblack/prompt-engineering/tree/main/week3/scraperbot).

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description                                                                                                                                                                         |
| ------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9/22/25 | 1h   | Attended lecture                                                                                                                                                                    |
| 9/24/25 | 1h   | Attended lecture                                                                                                                                                                    |
| 9/24/25 | 0.5h | Did some ideation on what kind of tool calling I want to implement                                                                                                                  |
| 9/25/25 | 2h   | Read [paper](https://arxiv.org/abs/2305.11853) on LLM text to SQL conversion techniques</br>Started building out prompts and infrastructure                                         |
| 9/26/25 | 2h   | Flesh out prompts, start testing tool connections                                                                                                                                   |
| 9/27/25 | 5h   | Build infrastructure for scraping arbitrary URLs<br>Containerize chatbot, which turned out to be a mistake<br>Debug MySQL auth error for two hours<br>Hotfix bugs up until midnight |

## Class notes

- Tools need to be registered in the OpenAI tool schema
  - Tools are arbitrary pieces of code that can be executed by an agent that has said tool enabled
  - Tools should have some kind of return schema that the agent can parse
  - Tool executes on the client machine (e.g. client environment)
  - Exercise: figure out how obtuse a prompt can be to trigger a tool call
- Track spending trends to get an idea of how much specific requests/models costs
  - This is useful for building at scale
- Idea: try to build a model that replicates OAI's deep learning magic
  - Containerize the sucker just in case
  - Play around with N8N workflow generation?
  - Try Whisper for text to speech
  - Build a scraper for some data, then do the SQL project to interface with it

## Findings

I heartily dislike Docker deciding that some environment variables change at runtime.

## Conclusions

AI interfacing with SQL is a nice way to demystify some of data science. This model was able to convert information from a number of websites into aggregate statistics, but the code as it currently stands is a buggy mess that I plan to refine.
