# Week 4: MCP time

## Executive Summary

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description                                                                                                                |
| ------- | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| 9/29/25 | 0.5h | Read [article](https://blog.cloudflare.com/code-mode/) on improving TypeScript MCP config                                  |
| 9/29/25 | 1h   | Attended lecture                                                                                                           |
| 9/30/25 | 3h   | Read up on [Cloudflare JS SDK](https://github.com/cloudflare/agents-starter)<br>Fix the scraperbot properly from last week |

## Class notes

- MCP defines a standard interface for an agent to connect to tools and data
  - Works with stdio or HTTPS
  - Each vendor defines tool calls differently, MCP provides a standard for how tools are defined & interpreted
  - Local tool calling is limited to one machine, MCP servers allow connections from any MCP-capable agent
  - More infrastructure/boilerplate but reusable
  - `fastmcp` is one of the more common Python libraries for defining MCP tools
    - use fastmcp.cloud if you don't want to try stdio
  - Try using `fastmcp` instead of ToolBox from last week in the same context
- Scott Lyon visit
  - Builds AI integrations for religious communities
  - Much of the work is tagging proprietary content in a schema such that an AI knows how to search/parse the data in a structured way
  - Garbage can theory: Decisions are rarely made cleanly and involve more processes than an outsider may immediately understand, seems semi-random
    - Generally better to use an existing system ("garbage can") rather than enforce a new one

## Exercises

## Findings

## Conclusions
