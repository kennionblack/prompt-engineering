import chromadb
from csv_parser import csv_to_chroma
from pathlib import Path

client = chromadb.PersistentClient(path="./chroma_db")

BATCH_SIZE = 5000


# ChromaDB apparently has a max batch size limit of 5461, hence this function
def batch_add_to_collection(
    collection: chromadb.Collection,
    ids: list[str],
    embeddings: list[float],
    metadatas: list[dict[str, str]],
    documents: list[str],
):

    total_docs = len(ids)

    for i in range(0, total_docs, BATCH_SIZE):
        end_idx = min(i + BATCH_SIZE, total_docs)

        collection.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            metadatas=metadatas[i:end_idx],
            documents=documents[i:end_idx],
        )


def populate_chroma():
    free_cluster_collection = client.get_or_create_collection(name="free_cluster")

    (
        free_cluster_ids,
        free_cluster_embeddings,
        free_cluster_metadatas,
        free_cluster_documents,
    ) = csv_to_chroma(
        Path("./free/free_3_clusters.csv"),
        metadata_fields=["source", "url"],
    )

    batch_add_to_collection(
        free_cluster_collection,
        free_cluster_ids,
        free_cluster_embeddings,
        free_cluster_metadatas,
        free_cluster_documents,
    )

    free_paragraph_collection = client.get_or_create_collection(name="free_paragraph")

    (
        free_paragraph_ids,
        free_paragraph_embeddings,
        free_paragraph_metadatas,
        free_paragraph_documents,
    ) = csv_to_chroma(
        Path("./free/free_paragraphs.csv"),
        metadata_fields=["source", "url"],
    )

    batch_add_to_collection(
        free_paragraph_collection,
        free_paragraph_ids,
        free_paragraph_embeddings,
        free_paragraph_metadatas,
        free_paragraph_documents,
    )

    free_talks_collection = client.get_or_create_collection(name="free_talks")

    (
        free_talks_ids,
        free_talks_embeddings,
        free_talks_metadatas,
        free_talks_documents,
    ) = csv_to_chroma(
        Path("./free/free_talks.csv"),
        metadata_fields=["source", "url"],
    )

    batch_add_to_collection(
        free_talks_collection,
        free_talks_ids,
        free_talks_embeddings,
        free_talks_metadatas,
        free_talks_documents,
    )

    openai_cluster_collection = client.get_or_create_collection(name="openai_cluster")
    (
        openai_cluster_ids,
        openai_cluster_embeddings,
        openai_cluster_metadatas,
        openai_cluster_documents,
    ) = csv_to_chroma(
        Path("./openai/openai_3_clusters.csv"),
        metadata_fields=["source", "url"],
        is_free=False,
    )

    batch_add_to_collection(
        openai_cluster_collection,
        openai_cluster_ids,
        openai_cluster_embeddings,
        openai_cluster_metadatas,
        openai_cluster_documents,
    )

    openai_paragraph_collection = client.get_or_create_collection(name="openai_paragraph")

    (
        openai_paragraph_ids,
        openai_paragraph_embeddings,
        openai_paragraph_metadatas,
        openai_paragraph_documents,
    ) = csv_to_chroma(
        Path("./openai/openai_paragraphs.csv"),
        metadata_fields=["source", "url"],
        is_free=False,
    )

    batch_add_to_collection(
        openai_paragraph_collection,
        openai_paragraph_ids,
        openai_paragraph_embeddings,
        openai_paragraph_metadatas,
        openai_paragraph_documents,
    )

    openai_talks_collection = client.get_or_create_collection(name="openai_talks")

    (
        openai_talks_ids,
        openai_talks_embeddings,
        openai_talks_metadatas,
        openai_talks_documents,
    ) = csv_to_chroma(
        Path("./openai/openai_talks.csv"),
        metadata_fields=["source", "url"],
        is_free=False,
    )

    batch_add_to_collection(
        openai_talks_collection,
        openai_talks_ids,
        openai_talks_embeddings,
        openai_talks_metadatas,
        openai_talks_documents,
    )
