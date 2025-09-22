# Week 0: Class Introduction

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date   | Time | Description                                                                                                                                                                                                                                                                                                                                  |
| ------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9/3/25 | 1h   | Attended lecture, read syllabus, joined Discord                                                                                                                                                                                                                                                                                              |
| 9/4/25 | 3h   | Prompt engineering research:<br>- [Anthropic overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) <br>- [oneusefulthing.org](https://www.oneusefulthing.org) articles and research papers<br>- Ideation on potential AI prompt engineering projects <br> - Set up Github repo for testing environment |
| 9/5/25 | 3h   | Prompt engineering exercise (for work)                                                                                                                                                                                                                                                                                                       |

## 9/4 Notes

### Maximizing prompt efficiency

I've heard the term "prompt engineering" thrown around for a while, but I was never sure what it was or why people invested so much time into it. As such, I decided to look into some of the main principles behind prompt engineering to get an idea of how best to maximise my model usage for the rest of class.

Below are my notes for what I was able to learn from my research. I did try to

- Positive instructions: using _do_ statements instead of _do not_ statements when possible
  - For some reason, AI models tend to parse this kind of instruction better.
  - Example: "Do not violate web accessibility standards" can become "Ensure that all accessibility guidelines for web content are followed"
- CoT prompting: split one large task into subtasks and feed these prompts interatively to the model for increased accuracy and depth
  - This has somewhat reduced efficiency when using newer reasoning models. Time cost to craft and split prompts [may not be worth it](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/).
- Zero-shot/few-shot prompting: providing minimal examples to an AI model with a well crafted prompt to perform a task
  - Relies on generalized knowledge from the AI
  - This tends to work better with specialized models that have good preexisting data for a specific topic, like a custom RAG
- Multishot prompting: providing multiple high fidelity examples to a model
  - From a statistical perspective, AI is much better at imitating existing data/ideas than actual original thought. As such, quality data and examples give it a strong "reference point" to formulate its responses.
  - Example: if an agent is supposed to generate a JSON object from a customer review, providing a schema and a number of pre-parsed customer reviews will help inform the agent what and how data should be stored.
  - Generating high fidelity examples is often time consuming, especially when the prompt writer themselves is not perfectly clear about what they want. As a general rule, when there is ambiguity in a prompt, there is higher risk of AI hallucination or necessary hidden assumptions.
    - It appears that some of the newer AI models are trending towards tackling this issue with more specific system prompts (e.g. some [GPT prompt leaks](https://news.ycombinator.com/item?id=44832990) specify using Tailwind when CSS is required).
- Metaprompting: writing a prompt to solve a problem with another AI
  - One agent can be optimized to write prompts with examples of tone and reasoning paths to feed into another AI. Anthropic has a metaprompt generator [here](https://colab.research.google.com/drive/1SoAajN8CBYTl79VyTwxtxncfCWlHlyy9#scrollTo=OryPPve8Gf5S) optimized for their models.
    - Anthropic leverages XML tags to delineate specific sections and reasoning approaches in conjunction with other prompt engineering techniques. Given that they promote this particular method in their prompt engineering guide, it seems reasonable to assume that Claude models have been trained to work with this style of prompting.
  - This style of prompting can help generate a "family" of agents that have similar tone, content boundaries, etc. without needing to craft
  - At what point is it time/cost prohibitive to use one AI model to talk to other AI models?
- Prefilling: Explicitly specifying how an agent should begin its response
  - Primary reasons to use this are to trim out some of the AI bloat in a response ("Sure, here's a list of...") or force specific responses in certain situations
  - One possible application of this technique is to prefill a `{` character into an agent that is only supposed to output JSON. Placing the `{` character first ensures that extraneous text is not prepended to a response.

## 9/5 Prompt Engineering Practice

There is currently an initiative at my work (FamilySearch) to determine the effectiveness of using AI to solve accessibility issues on the website. To investigate this, a developer created a test repository with two major WCAG issues and challenged other developers in the org to solve these issues exclusively with AI. For proprietary reasons, I can't share the prompts that I used or the code that was generated by the AI models that I used, but I can share the challenge rules and my findings from this exercise.

Here is the challenge description:

```
Using the two tickets found under the /bugs folder, try to use AI to resolve the problems.

These issues are deceptively difficult to solve. I expect AI can eventually solve TICKET-1, but I doubt it can solve TICKET-2.

I'd love to have someone show me a valid solution to this problem generated with AI.

Rules:
- You can only use AI
- You can't use any 3rd party libraries that may have already solved this problem. (including ZionUI)
- You can look at any docs you want, except for looking at the working solution inside source code
- Should you know the correct solutions, you are not allowed to dictate to the AI what that solution is

How to submit a solution:
- Submit a PR
- Include in the PR title and/or description which Agent/IDE you were using. For example: VS Code + GPT-5 or Claude Code
- Copy your prompts and/or agent's conversation (as much as possible) to a txt or md file add attach it to the PR description (for traceability).

A developer will review it and let you know what accessibility problems still exist, if any.
```

My method to solving this was to generate a metaprompt with the org's Copilot subscription, then feed this metaprompt into the Claude agent in VSCode to solve the issue. Generating the metaprompt itself proved to be more difficult than originally anticipated--I used the Anthropic template linked previously as a starting point, but I found that I had to tweak the prompt that Copilot spit out a fair amount. Originally, Copilot just wrote (poor) directions to solve the bugs for the Claude agent to implement, but I was eventually able to coax Copilot into writing a prompt that emphasized minimal code changes and guiding principles for Claude to solve the problem on its own.

Given that the nature of the two bugs were already documented, I decided to use a test-driven development approach to first have Claude generate appropriate failing tests for the current issues. Claude was able to generate relatively useful Playwright tests and get the testing environment set up, but there were a number of times where I had to stop it mid-execution after it made unnecessary changes. I started to use more of a chain-of-thought prompting method as more and more issues cropped up and found that Claude generally did best with specific feedback from my manual tests on the website instead of its own acceptance criteria from the Playwright tests (especially because it often lobotomized failing tests until they passed instead of resolving the underlying issue).

I'd done some rudimentary prompting with Claude over the summer (without all the fancy prompt engineering techniques) and noted that the metaprompt did help Claude stay more on topic than I had previously observed. I also noticed that including good acceptance criteria in a prompt helps the AI have a more targeted goal than a "fix this" prompt. I think that this exercise was overall useful in helping me understand why crafting more thoughtful prompts has tangible effects on the quality of AI generated code.
