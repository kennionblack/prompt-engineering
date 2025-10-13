# Week 5: RAG 'n Bone

## Executive Summary

This week I built two RAG systems: a podcast recommender using PostgreSQL with pgvector and a comprehensive conference talk RAG using ChromaDB. I explored multiple embedding approaches and compared OpenAI embeddings against free embedding models. ChromaDB proved significantly more user-friendly than PostgreSQL for vector operations, though both platforms successfully handled semantic search at scale.

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date     | Time | Description                                                                                                                                 |
| -------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 10/6/25  | 1h   | Attended lecture                                                                                                                            |
| 10/7/25  | 5h   | Figure out how to use SQL to perform efficient vector comparisons<br>Build Postgres semantic search recommender with L2 distance comparison |
| 10/8/25  | 1h   | Attend lecture                                                                                                                              |
| 10/11/25 | 5h   | Learn how to use ChromaDB<br>Learn how to generate embedding vectors<br>Build conference talk RAG for multiple embedding vector approaches  |

## Class notes

- Retrieval Augmented Generation (RAG)
  - Process of retrieving additional information from an extenral source of knowledge & feeding it into query context
  - Adds "new" information for the model's response
  - Restricts responses to provided context (reduced hallucination)
  - User query hits an "embedder", which splits request into chunks that can be compared against chunks stored in a vector database
    - Data is pre-chunked into the database
    - Results from vector DB are fed into "reranker", which analyses results returned
    - Reranker result and embedded query are fed into LLM, which generates a response
  - Embeddings
    - Numerical representation of text (vector)
    - SImilar texts should be close in vector space
    - Semantic search compared query vectors to content vectos with distance metrics (cosine similarity or dot product)
  - Transformers
    - Encoder stack converts text ond other media into an embedding vector
      - Many network layers perform this function in sequence
      - Some LLMs only embed text without decoding
    - Decoder stack parses embedded vectors into understandable tokens
    - More layers generally improves quality but takes a hit on performance
  - Some of the salient questions with RAG these days are [here](https://www.datacamp.com/blog/rag-interview-questions)
  - Dot product of embedding vectors is between 0 and 1
    - The closer something is to 1, the more similar it is
    - Cosine similarity normalizes better and minimizes extraneous results
    - Good embedders should distill similar concepts to similar vectors such that this kind of comparison can be made

## Exercises

Most of my work this week was in conjunction with my CS 452 class, which also happened to be teaching vector databases and RAG this week.

### Recommender project

The first project description is as follows: "In this lab we will build a small-scale podcast recommender system using the science and technology podcast The Lex Fridman Podcast. Specifically, we will use GPT models from OpenAI to embed podcast segments into a vector space. We will load these vectors into a postgres database with the pgvector extension enabled. Finally, we will write queries to find similar segments and similar episodes to an input podcast segment."

This project necessitated loading data from .jsonl files into Postgres, then crafting Postgres queries to determine what other vectors were most similar to a provided target vector.

Code is [here](https://github.com/kennionblack/prompt-engineering/tree/main/week5/recommender).

### Conference talk RAG

The second project description is as follows: "In this assignment, we will create a program that can take a string input, and return three Latter-day Saint General Conference talks that are the most similar. The database of conference talks and embeddings are provided, but we can give it whatever input we want. We will have to take the provided input and create an embedding out of it using the SentenceTransformer module. We will then manually code the algorithm to compare that embedding with every single conference talk embedding in the database. The three talks with the highest similarity values will be returned.

In the second part of this assignment, the three conference talks will be sent to ChatGPT, and you will instruct it to answer the original string input by only referencing the talks, and not consult outside sources. Please feel free to experiment and do the semantic search and embeddings in a way that is interesting to you. Please try multiple ways and compare and contrast results. Engineer good prompts that work really well for your workflow."

I used ChromaDB for this project instead of Postgres, which was a nice change of pace. The data for the talks was scraped from the past 7 years of Conference talks on the Church website. This RAG precomputes the questions instead of providing a live user interface, but it would be relatively simple to convert this into something that an actual user could use.

Code is [here](https://github.com/kennionblack/prompt-engineering/tree/main/week5/conference-rag).

## Findings/Conclusions

I was pleasantly surprised with how well Postgres was able to handle vector types and vector computations. However, ChromaDB was _significantly_ easier to use because a simple similarity query in ChromaDB took a 15+ line SQL statement.

Analysis of the different embedding methods used for the conference RAG can be found [here](https://github.com/kennionblack/prompt-engineering/tree/main/week5/conference-rag/analysis.txt).
