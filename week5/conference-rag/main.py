from chroma_insert import populate_chroma
from question_conversion import (
    questions_to_free_embeddings,
    questions_to_openai_embeddings,
)
import chromadb
import os
from dotenv import load_dotenv
from openai import OpenAI
import asyncio


def get_top_k_results(
    question: str,
    embedding_dict: dict[str, list[float]],
    collection: chromadb.Collection,
    k=3,
):
    question_embedding = embedding_dict[question]
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=k,
        include=["metadatas", "documents", "distances"],
    )

    retrieved_docs = []
    if results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            doc_info = {
                "distance": results["distances"][0][i],
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            }
            retrieved_docs.append(doc_info)

    return retrieved_docs


class RAGClient:
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.system_prompt = "You are a RAG-powered assistant that provides accurate and comprehensive answers based on the provided context documents."

    def format_context(self, retrieved_docs: list[dict]) -> str:
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            doc_text = doc["document"]
            if isinstance(doc_text, list):
                doc_text = str(doc_text)

            metadata = doc["metadata"] or {}
            title = metadata.get("title", "Unknown Title")
            speaker = metadata.get("speaker", "Unknown Speaker")
            year = metadata.get("year", "Unknown Year")
            url = metadata.get("url", metadata.get("source_url", ""))

            context_parts.append(
                f"Document {i} (Similarity Score: {1 - doc['distance']:.4f}):\n"
                f"Title: {title}\n"
                f"Speaker: {speaker}\n"
                f"Year: {year}\n"
                f"Content: {doc_text}"
            )

        return "\n\n".join(context_parts)

    def generate_response(self, question: str, retrieved_docs: list[dict]) -> str:
        context = self.format_context(retrieved_docs)

        prompt = f"""
        Based on the following retrieved documents from LDS General Conference talks, please answer the provided question. 
        Use the information from the documents to provide a comprehensive and accurate response.
        
        When referencing information from the documents, please mention the speaker's name and/or talk title when relevant.

        Question: {question}

        Retrieved Documents:
        {context}

        Please provide a thoughtful answer based on the information in these documents. 
        
        If the documents don't contain relevant information for the question, please still answer the question with the information from the provided documents, but also indicate that the results may not be trustworthy.
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )

        return response.choices[0].message.content

    def extract_urls(self, retrieved_docs: list[dict]) -> list[str]:
        """Extract URLs from retrieved documents"""
        urls = []
        for doc in retrieved_docs:
            metadata = doc["metadata"] or {}
            url = metadata.get("url", metadata.get("source_url", ""))
            if url:
                urls.append(url)
        return urls

    def query(self, question: str, retrieved_docs: list[dict]) -> dict:
        """Main RAG query method"""
        response = self.generate_response(question, retrieved_docs)
        urls = self.extract_urls(retrieved_docs)

        # Add URLs deterministically to the response
        if urls:
            url_section = "\n\nSource URLs:\n" + "\n".join(f"- {url}" for url in urls)
            full_response = response + url_section
        else:
            full_response = response

        return {
            "question": question,
            "response": full_response,
            "source_docs": retrieved_docs,
            "num_docs_used": len(retrieved_docs),
            "source_urls": urls,
        }


if __name__ == "__main__":
    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    rag_client = RAGClient(openai_client)

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

    collections = {
        "free_talks": chromadb_client.get_collection(name="free_talks"),
        "free_paragraphs": chromadb_client.get_collection(name="free_paragraphs"),
        "free_clusters": chromadb_client.get_collection(name="free_clusters"),
        "openai_talks": chromadb_client.get_collection(name="openai_talks"),
        "openai_paragraphs": chromadb_client.get_collection(name="openai_paragraphs"),
        "openai_clusters": chromadb_client.get_collection(name="openai_clusters"),
    }

    for question in questions:
        print(f"\n{'='*80}")
        print(f"QUESTION: {question}")
        print(f"{'='*80}")

        # Test with free embeddings on talks collection
        free_results = get_top_k_results(
            question, free_question_embeddings, collections["free_talks"], k=3
        )

        if free_results:
            print(f"\n--- FREE EMBEDDINGS (TALKS) ---")
            rag_response = rag_client.query(question, free_results)
            print(f"Response: {rag_response['response']}")
            print(f"Used {rag_response['num_docs_used']} source documents")

        # Test with OpenAI embeddings on talks collection
        openai_results = get_top_k_results(
            question, openai_question_embeddings, collections["openai_talks"], k=3
        )

        if openai_results:
            print(f"\n--- OPENAI EMBEDDINGS (TALKS) ---")
            rag_response = rag_client.query(question, openai_results)
            print(f"Response: {rag_response['response']}")
            print(f"Used {rag_response['num_docs_used']} source documents")
