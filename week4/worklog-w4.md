# Week 4: MCP time

## Executive Summary

This week was focused on building agents in Typescript, then getting a Typescript MCP server up and running. I successfully implemented both an MCP server and client CLI with MCP tool ingestion and natural language contextualization of tool results.

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description                                                                                                                                                                    |
| ------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 9/29/25 | 0.5h | Read [article](https://blog.cloudflare.com/code-mode/) on improving TypeScript MCP config                                                                                      |
| 9/29/25 | 1h   | Attended lecture                                                                                                                                                               |
| 9/30/25 | 3h   | Read up on [Cloudflare JS SDK](https://github.com/cloudflare/agents-starter)<br>Fix the scraperbot properly from last week                                                     |
| 10/1/25 | 1h   | Attended lecture                                                                                                                                                               |
| 10/3/25 | 3h   | Get Cloudflare starter agent up and running<br>Get a simple TypeScript chatbot working                                                                                         |
| 10/4/25 | 2h   | Get SQL natural language interface for an actual database working<br>Convert TypeScript chatbot to run both an MCP server and an MCP client that can make tool calls as needed |

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

I spent a good amount of time this week figuring out how to do agent development in Typescript. I first made a Typescript chatbot with a couple basic tool calls, then used that codebase as a starting point for a Typescript MCP server and MCP client.

## Findings

Python is much faster to prototype this kind of development in, but I do like how tool schemas are laid out better in Typescript (partially because JS and JSON are friends). Copilot was a great help in getting these chatbots up and running quickly, especially when I don't know the agent libraries in JS yet.

Tool calling and MCP seem to be largely the same idea (at least from a user perspective), but I can appreciate how MCP makes tools generally accessible without needing a whole environment setup.

## Conclusions

With the proliferation of AI agents in nearly all consumer-facing products, it follows that most languages will have some good agentic libraries in place. I do a lot of Javascript for my current job so I'm slightly partial to this over Python, but I don't see major differences in functionality thus far.

I'm planning on building a generic Typescript starter agent that I can iterate on in the future to eliminate a lot of the boilerplate that went into this week. I also want to get the Cloudflare MCP to API conversion thing working that I mentioned in the worklog, but there wasn't time for that this week.
