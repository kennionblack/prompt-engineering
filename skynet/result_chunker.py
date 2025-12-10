"""
Intelligent chunking for large results to prevent context window overflow.

This module provides utilities to automatically detect and chunk large results
based on token counts, preserving all information while staying within model
context window limits.
"""

import json
import tiktoken
from typing import Dict, Any, List

# Token counting for chunking
try:
    _encoding = tiktoken.encoding_for_model("gpt-4o")
except Exception:
    _encoding = tiktoken.get_encoding("cl100k_base")

# Conservative limits to prevent context overflow for gpt-5-mini (128k context)
# Leave significant room for conversation history, prompt, and tool definitions
MAX_RESULT_TOKENS = 8000  # Very conservative: only ~6% of context for single result
CHUNK_SIZE_TOKENS = 6000  # Smaller chunks for better handling
MAX_CHUNKS_TO_RETURN = 2  # Only return first 2 chunks to avoid overwhelming context


def count_tokens(text: str) -> int:
    """Count tokens in a string using tiktoken"""
    try:
        return len(_encoding.encode(text))
    except Exception:
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4


def chunk_large_result(
    result: Any, max_tokens: int = MAX_RESULT_TOKENS
) -> Dict[str, Any]:
    """
    Chunk large results to prevent context window overflow.

    Args:
        result: The result to potentially chunk
        max_tokens: Maximum tokens before chunking

    Returns:
        Either the original result or a chunked version with metadata
    """
    # Convert result to JSON string to measure size
    try:
        result_json = json.dumps(result)
        token_count = count_tokens(result_json)

        # If small enough, return as-is
        if token_count <= max_tokens:
            return result

        # Result is too large - chunk it
        print(f"⚠️  Large result detected ({token_count:,} tokens), chunking...")

        # Try to chunk intelligently based on result type
        if isinstance(result, dict):
            return _chunk_dict_result(result, max_tokens)
        elif isinstance(result, list):
            return _chunk_list_result(result, max_tokens)
        elif isinstance(result, str):
            return _chunk_string_result(result, max_tokens)
        else:
            # Unknown type, convert to string and chunk
            return _chunk_string_result(str(result), max_tokens)

    except Exception as e:
        print(f"⚠️  Chunking failed: {e}, returning original result")
        return result


def _chunk_dict_result(result: dict, max_tokens: int) -> Dict[str, Any]:
    """Chunk a dictionary result by extracting large fields"""
    # Common large fields in web fetch results
    large_fields = ["text", "content", "html", "body", "data", "content_base64"]

    chunked = {
        "__chunked__": True,
        "__chunk_reason__": "Result too large for context window",
        "metadata": {},
        "chunks": [],
    }

    # Separate small metadata from large content
    large_content = {}
    for key, value in result.items():
        try:
            value_json = json.dumps(value)
            value_tokens = count_tokens(value_json)

            if key in large_fields and value_tokens > CHUNK_SIZE_TOKENS:
                large_content[key] = value
            else:
                chunked["metadata"][key] = value
        except (TypeError, ValueError):
            # Can't serialize, include in metadata
            chunked["metadata"][key] = (
                str(value)[:1000] + "..." if len(str(value)) > 1000 else str(value)
            )

    # Chunk the large content fields
    if large_content:
        for field_name, field_value in large_content.items():
            if isinstance(field_value, str):
                field_chunks = _split_text_into_chunks(field_value, CHUNK_SIZE_TOKENS)

                # Only include first MAX_CHUNKS_TO_RETURN chunks to avoid context overflow
                chunks_to_include = min(len(field_chunks), MAX_CHUNKS_TO_RETURN)

                for i in range(chunks_to_include):
                    chunk_text = field_chunks[i]
                    chunked["chunks"].append(
                        {
                            "chunk_index": i + 1,
                            "total_chunks": len(field_chunks),
                            "field": field_name,
                            "content": chunk_text,
                            "tokens": count_tokens(chunk_text),
                        }
                    )

                # Add note if there are more chunks
                if len(field_chunks) > MAX_CHUNKS_TO_RETURN:
                    chunked["__truncated__"] = True
                    chunked["__remaining_chunks__"] = (
                        len(field_chunks) - MAX_CHUNKS_TO_RETURN
                    )
                    chunked["__note__"] = (
                        f"Content too large. Showing first {MAX_CHUNKS_TO_RETURN} of {len(field_chunks)} chunks. Remaining content truncated to prevent context overflow."
                    )
            else:
                # Non-string large field, include in metadata with truncation note
                chunked["metadata"][field_name] = "<large non-text field, truncated>"

    chunked["total_chunks"] = len(chunked["chunks"])
    return chunked


def _chunk_list_result(result: list, max_tokens: int) -> Dict[str, Any]:
    """Chunk a list result into smaller batches"""
    chunks = []
    current_chunk = []
    current_tokens = 0

    for item in result:
        try:
            item_json = json.dumps(item)
            item_tokens = count_tokens(item_json)

            if current_tokens + item_tokens > CHUNK_SIZE_TOKENS and current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk)
                current_chunk = [item]
                current_tokens = item_tokens
            else:
                current_chunk.append(item)
                current_tokens += item_tokens
        except (TypeError, ValueError):
            # Can't serialize item, add as string
            current_chunk.append(str(item))

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Only return first MAX_CHUNKS_TO_RETURN chunks
    chunks_to_include = min(len(chunks), MAX_CHUNKS_TO_RETURN)

    result_dict = {
        "__chunked__": True,
        "__chunk_reason__": "List too large for context window",
        "total_items": len(result),
        "chunks": [
            {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "items": chunks[i - 1],
                "item_count": len(chunks[i - 1]),
                "tokens": count_tokens(json.dumps(chunks[i - 1])) if chunks[i - 1] else 0,
            }
            for i in range(1, chunks_to_include + 1)
        ],
        "total_chunks": len(chunks),
    }

    # Add truncation note if needed
    if len(chunks) > MAX_CHUNKS_TO_RETURN:
        result_dict["__truncated__"] = True
        result_dict["__remaining_chunks__"] = len(chunks) - MAX_CHUNKS_TO_RETURN
        result_dict["__note__"] = (
            f"List too large. Showing first {MAX_CHUNKS_TO_RETURN} of {len(chunks)} chunks. Remaining items truncated to prevent context overflow."
        )

    return result_dict


def _chunk_string_result(result: str, max_tokens: int) -> Dict[str, Any]:
    """Chunk a string result into smaller pieces"""
    chunks = _split_text_into_chunks(result, CHUNK_SIZE_TOKENS)

    # Only return first MAX_CHUNKS_TO_RETURN chunks
    chunks_to_include = min(len(chunks), MAX_CHUNKS_TO_RETURN)

    result_dict = {
        "__chunked__": True,
        "__chunk_reason__": "String too large for context window",
        "total_length": len(result),
        "chunks": [
            {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content": chunks[i - 1],
                "length": len(chunks[i - 1]),
                "tokens": count_tokens(chunks[i - 1]),
            }
            for i in range(1, chunks_to_include + 1)
        ],
        "total_chunks": len(chunks),
    }

    # Add truncation note if needed
    if len(chunks) > MAX_CHUNKS_TO_RETURN:
        result_dict["__truncated__"] = True
        result_dict["__remaining_chunks__"] = len(chunks) - MAX_CHUNKS_TO_RETURN
        result_dict["__note__"] = (
            f"String too large. Showing first {MAX_CHUNKS_TO_RETURN} of {len(chunks)} chunks. Remaining content truncated to prevent context overflow."
        )

    return result_dict


def _split_text_into_chunks(text: str, chunk_size_tokens: int) -> List[str]:
    """Split text into chunks of approximately chunk_size_tokens each"""
    if not text:
        return []

    # Approximate: 1 token ≈ 4 characters
    approx_chunk_size_chars = chunk_size_tokens * 4

    # Try to split on natural boundaries (paragraphs, sentences)
    chunks = []
    current_chunk = ""

    # Split on double newlines first (paragraphs)
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        para_tokens = count_tokens(current_chunk + para)

        if para_tokens > chunk_size_tokens and current_chunk:
            # Current chunk is full, save it
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += ("\n\n" if current_chunk else "") + para

        # If single paragraph is too large, split it further
        if count_tokens(current_chunk) > chunk_size_tokens * 1.5:
            # Force split at character boundary
            while len(current_chunk) > approx_chunk_size_chars:
                split_point = approx_chunk_size_chars
                # Try to split at sentence boundary
                sentence_end = current_chunk.rfind(". ", 0, split_point + 100)
                if sentence_end > split_point - 500:
                    split_point = sentence_end + 2

                chunks.append(current_chunk[:split_point].strip())
                current_chunk = current_chunk[split_point:]

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]
