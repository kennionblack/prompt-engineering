import os
import json
from dotenv import load_dotenv
from datasets import load_dataset
import pandas as pd
from pathlib import Path

from utils import fast_pg_insert

load_dotenv()

CONNECTION_STRING = os.getenv("TIMESCALE_CONNECTION_STRING")

# Parse all embedding .jsonl files into JSON objects
embeddings_path = Path("./data/lex-fridman-text-embedding-3-large-128/embeddings")
embeddings = []

for file_path in embeddings_path.glob("*.jsonl"):
    with file_path.open() as file:
        for line in file:
            embeddings.append(json.loads(line))

# Parse all document .jsonl files into JSON objects
documents_path = Path("./data/lex-fridman-text-embedding-3-large-128/documents")
documents = []

for file_path in documents_path.glob("*.jsonl"):
    with file_path.open() as file:
        for line in file:
            documents.append(json.loads(line))

# Create podcast rows from documents
podcast_rows = []
podcast_ids = set()
for document in documents:
    curr_id = document["body"]["metadata"]["podcast_id"]
    if curr_id not in podcast_ids:
        podcast_rows.append(
            {
                "id": document["body"]["metadata"]["podcast_id"],
                "title": document["body"]["metadata"]["title"],
            }
        )
        podcast_ids.add(curr_id)

# Map custom id to embedding vector such that we can access it in the segment creation
embedding_map = {}
for embedding in embeddings:
    embedding_map[embedding["custom_id"]] = embedding["response"]["body"]["data"][0]["embedding"]

# Create segment rows from documents and mapped embedding vector
segment_rows = []
for document in documents:
    segment_rows.append(
        {
            "id": document["custom_id"],
            "start_time": document["body"]["metadata"]["start_time"],
            "end_time": document["body"]["metadata"]["stop_time"],
            "content": document["body"]["input"],
            "embedding": embedding_map.get(document["custom_id"]),
            "podcast_id": document["body"]["metadata"]["podcast_id"],
        }
    )

# Convert to dataframes for fast_pg_insert
podcast_rows_df = pd.DataFrame(podcast_rows)
segment_rows_df = pd.DataFrame(segment_rows)

podcast_columns = ["id", "title"]
segment_columns = ["id", "start_time", "end_time", "content", "embedding", "podcast_id"]

# Chunk rows into smaller size to avoid memory errors
chunk_size = 20000
for i in range(0, len(podcast_rows_df), chunk_size):
    chunk = podcast_rows_df.iloc[i : i + chunk_size]
    fast_pg_insert(chunk, CONNECTION_STRING, "podcast", podcast_columns)

for i in range(0, len(segment_rows_df), chunk_size):
    chunk = segment_rows_df.iloc[i : i + chunk_size]
    fast_pg_insert(chunk, CONNECTION_STRING, "podcast_segment", segment_columns)
