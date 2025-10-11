import csv
from pathlib import Path
from typing import List


def csv_to_chroma(file_path: Path, metadata_fields: List[str], is_free=True):
    ids = []
    embeddings = []
    metadatas = []
    documents = []

    reader = csv.DictReader(file_path.open())
    for index, row in enumerate(reader):
        # this should be unique enough
        # chroma expects a list of strings for ids, so we cast the index to a string
        ids.append(str(index))

        embeddings.append(parse_embedding_string(row["embedding"], is_free))

        metadatas.append(parse_metadata(row, metadata_fields))

        # all of the csvs use text as the column name for the actual text
        documents.append(row["text"])

    return ids, embeddings, metadatas, documents


def parse_embedding_string(embedding_str: str, is_free):
    try:
        # Parse the embedding string as a Python list using ast.literal_eval
        import ast

        embedding_list = ast.literal_eval(embedding_str)
        return [float(x) for x in embedding_list]
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing embedding: {e}")
        if is_free:
            # Dimensionality of free text embeddings is 384
            return [0.0] * 384
        else:
            # Dimensionality of OpenAI text embeddings is 1536
            return [0.0] * 1536


def parse_metadata(row: dict, metadata_fields: List[str]):
    metadata = {}
    for field in metadata_fields:
        if field in row:
            metadata[field] = row[field]
    return metadata
