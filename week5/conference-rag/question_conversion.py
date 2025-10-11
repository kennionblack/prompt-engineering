from sentence_transformers import SentenceTransformer
import torch
from openai import OpenAI
import tiktoken
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Replicate the embedding process from free_embeddings.py to generate embeddings for questions
def questions_to_free_embeddings(questions: List[str]) -> Dict[str, List[float]]:
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        if torch.cuda.is_available():
            model = model.to("cuda")
            print("Using GPU for encoding")
        else:
            print("Using CPU for encoding")

        embeddings = model.encode(
            questions,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

        # Map questions to their respective embeddings
        question_embedding_map = {}
        for question, embedding in zip(questions, embeddings):
            question_embedding_map[question] = embedding

        return question_embedding_map

    except Exception as e:
        print(f"Error in questions_to_free_embeddings: {e}")
        # Return empty embeddings (384 dimensions) for all questions as fallback
        return {question: [0.0] * 384 for question in questions}


# Replicate the embedding process from openai_embeddings.py to generate embeddings for questions
def questions_to_openai_embeddings(questions: List[str]) -> Dict[str, List[float]]:
    try:
        model = "text-embedding-3-small"
        max_tokens = 300000

        encoder = tiktoken.encoding_for_model(model)

        cleaned_questions = [question.replace("\n", " ") for question in questions]
        token_counts = [len(encoder.encode(question)) for question in cleaned_questions]

        embeddings = []
        current_batch = []
        current_token_count = 0

        for i, (question, token_count) in enumerate(zip(cleaned_questions, token_counts)):
            if (
                current_token_count + token_count > max_tokens
                or len(current_batch) >= 100
            ):
                # Process current batch
                response = client.embeddings.create(input=current_batch, model=model)
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                # Reset batch
                current_batch = [question]
                current_token_count = token_count
            else:
                current_batch.append(question)
                current_token_count += token_count

        # Process final batch
        if current_batch:
            response = client.embeddings.create(input=current_batch, model=model)
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)

        # Map questions to their respective embeddings
        question_embedding_map = {}
        for question, embedding in zip(questions, embeddings):
            question_embedding_map[question] = embedding

        return question_embedding_map

    except Exception as e:
        print(f"Error in questions_to_openai_embeddings: {e}")
        # Return empty embeddings (1536 dimensions) for all questions as fallback
        return {question: [0.0] * 1536 for question in questions}
