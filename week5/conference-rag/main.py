from chroma_insert import populate_chroma
from question_conversion import (
    questions_to_free_embeddings,
    questions_to_openai_embeddings,
)
import chromadb
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI


def get_top_k_results(
    questions: list[str],
    embedding_dict: dict[str, list[float]],
    collection: chromadb.Collection,
    k=3,
):
    for question in questions:
        print(f"\nQuestion: {question}\n")
        question_embedding = embedding_dict[question]
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=k,
            include=["metadatas", "documents", "distances"],
        )

        # Format and display results nicely
        print("Top Results:")
        print("-" * 50)

        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                print(f"\nResult {i+1}:")
                print(f"  Distance: {results['distances'][0][i]:.4f}")

                # Display URL from metadata if available
                if results["metadatas"] and results["metadatas"][0][i]:
                    metadata = results["metadatas"][0][i]
                    if "url" in metadata:
                        print(f"  URL: {metadata['url']}")
                    elif "source_url" in metadata:
                        print(f"  URL: {metadata['source_url']}")

                # Display document preview if available
                if results["documents"] and results["documents"][0][i]:
                    doc = results["documents"][0][i]
                    if isinstance(doc, list):
                        print(f"  Preview: {str(doc)[:200]}...")
                    else:
                        print(f"  Preview: {doc[:200]}...")
        else:
            print("  No results found")

        print("=" * 50)


if __name__ == "__main__":
    # Initialize Chroma database if not already initialized
    if not os.path.exists("./chroma_db"):
        populate_chroma()

    questions = [
        "How can I gain a testimony of Jesus Christ?",
        "What are some ways to deal with challenges in life and find a purpose?",
        "How can I fix my car if it won't start?",
        "Why do bad things happen to good people?",
        "What is the meaning of life?",
    ]

    free_question_embeddings = questions_to_free_embeddings(questions)
    openai_question_embeddings = questions_to_openai_embeddings(questions)

    chromadb_client = chromadb.PersistentClient(path="./chroma_db")

    free_cluster_collection = chromadb_client.get_collection(name="free_cluster")
    free_paragraph_collection = chromadb_client.get_collection(name="free_paragraph")
    free_talk_collection = chromadb_client.get_collection(name="free_talks")

    openai_cluster_collection = chromadb_client.get_collection(name="openai_cluster")
    openai_paragraph_collection = chromadb_client.get_collection(name="openai_paragraph")
    openai_talk_collection = chromadb_client.get_collection(name="openai_talks")

    free_cluster_results = get_top_k_results(
        questions, free_question_embeddings, free_cluster_collection, k=3
    )
    free_paragraph_results = get_top_k_results(
        questions, free_question_embeddings, free_paragraph_collection, k=3
    )
    free_talk_results = get_top_k_results(
        questions, free_question_embeddings, free_talk_collection, k=3
    )

    openai_cluster_results = get_top_k_results(
        questions, openai_question_embeddings, openai_cluster_collection, k=3
    )
    openai_paragraph_results = get_top_k_results(
        questions, openai_question_embeddings, openai_paragraph_collection, k=3
    )
    openai_talk_results = get_top_k_results(
        questions, openai_question_embeddings, openai_talk_collection, k=3
    )

    load_dotenv()
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
