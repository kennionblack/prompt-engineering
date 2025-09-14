# Week 1: Yet More Prompt Engineering

## Executive Summary

This week's project was to create a translation web interface using both OpenAI and DeepL APIs that lets me compare English-to-Chinese translations side-by-side, complete with pinyin and ambiguity analysis. I built this as a personal study tool for my Chinese 101 class with some practical prompt engineering techniques while creating something actually useful for language learning that provides translation comparisons with letter grades and recommendations.

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description                                                                                                                                                                                                                                                                                                                                                           |
| ------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9/8/25  | 1h   | Attended lecture                                                                                                                                                                                                                                                                                                                                                      |
| 9/10/25 | 1h   | Attended lecture                                                                                                                                                                                                                                                                                                                                                      |
| 9/11/25 | 2h   | Researched model differences, eventually decided on ChatGPT<br>Got ChatGPT key, set up .env file                                                                                                                                                                                                                                                                      |
| 9/12/25 | 4h   | Used Gradio as staging ground for prompt engineering exercises<br>Scoured Internet and pypi for actually good modules for Chinese translation<br>Settled on DeepL module for translation comparison<br>Got DeepL API key and stored in .env<br>Set up prompt structure with JSON schema for original translation<br>Fine-tuned prompt to consistently get JSON output |
| 9/13/25 | 2h   | Got DeepL translation model up and running with pinyin_jyutping for pinyin output<br>Rewired Gradio interface to display the requisite information in an actually useful way<br>Wrote comparison prompt and added some async logic to help speed things up<br>Tested model with a number of semi-arbitrary strings                                                    |

## Exercises

My main exercise this week was building a simple web interface in Gradio for Chinese translation. I'm currently taking Chinese 101 and am working on improving my fluency with character recognition and pronunciation. I wrote a custom prompt for ChatGPT to translate an arbitrary string with notes on translation ambiguity and also used a general translation package (DeepL) for the same string. These two outputs are structured into a JSON model and fed to a new ChatGPT prompt that compares the two translations and assigns a letter grade to both translations with a detailed recommendation of which translation to use.

## Findings

### AI model differences

- The "Big 3" models seem to al have a basic, pro, and enterprise tier model. Pro costs are probably appropriate for this class
- Claude is good at code and debugging, but has a smaller context window which drives up cost
  - Probably the top model for software engineering
  - New features are driving "one-stop shop" approach where Claude can now generate Microsoft file formats, parse data betweeen file types, etc.
- Gemini is also solid but lacks polish, in areas where its training data is rich it can provide real value but can also go completely off the rails sometimes
  - Has potential but for the moment needs some fine tuning on the Google side of things
  - Likely will be tightly integrated with the whole Google suite in educational contexts, so worth getting used to it
    - Google search is currently shoving it down everyone's throat but it seems at least okay
  - Video and image generation is where Gemini stands out
- ChatGPT is probably the most well-rounded, especially when it comes to tone
  - GPT-5 seems to have been particularly trained to avoid the "sycophancy as a service" moniker
  - Microsoft seems to be backing this one primarily, which is a plus for most enterprises

### Chinese translation

- Chinese is a difficult language to translate appropriately due to a number of cultural and structural differences
- The most reliable translation APIs/packages are largely behind paywalls
  - DeepL looks decent and has a free tier with 500,000 words per month, which is more than enough for this project
  - DeepL themselves purport to use AI, which should make this an interesting comparison
- Converting Mandarin to pinyin should be a largely one-to-one translation, yet the modules for this are depressingly lacking
  - `pinyin` package is the easiest to boot up, but a number of people argue that the transliteration is sloppy for large blocks of text
  - `pinyin_jyutping` is probably the best open source option for the time being

## Conclusions

I mostly did this exercise to determine how I might want to (somewhat) automate translation for phrases that I will encounter in my Chinese class. Depending on what time I can dedicate to this project throughout the semester, I might bake in voice recognition and audio practice to make this a more effective study tool.

It is a little frustrating that the same input and prompt will not always produce a deterministic output, but in the context of this project some flexibility is probably a good thing due to there not being one-to-one mappings from English to Chinese in every circumstance. Coding around LLM output does feel rather defensive, but I think the tradeoff is worth it in smaller to medium scale projects. I still wouldn't trust an LLM to output perfectly valid code, translations, etc. in a larger project as accounting for edge cases from hallucinations/bad output seems like more trouble than it's worth.

I do like the relative simplicity of Gradio for spinning up a web interface. It seems like Gradio was developed as a quick prototyping tool and I've been satisfied with the widgets and modularity that it provides.

Providing examples to an AI prompt do seem to improve its output, especially when I want said output to be in JSON. ChatGPT did try to make JSON into JavaScript objects occasionally, but I found a way to work around this in code to reduce the amount of variability from the prompt.
