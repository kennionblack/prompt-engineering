# Week 5: RAG 'n Bone

## Executive Summary

## Worklog

<!-- Note that this "table" was mostly generated with a VSCode extension that attempts to make all markdown table cells the same size, hence the strange formatting. I strongly recommend reading this report with something that actually renders the markdown instead of attempting to parse this mess visually. -->

| Date    | Time | Description      |
| ------- | ---- | ---------------- |
| 10/6/25 | 1h   | Attended lecture |

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

## Findings

## Conclusions
