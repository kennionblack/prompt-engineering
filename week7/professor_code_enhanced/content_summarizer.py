"""
Content Summarization Pipeline

Handles large content by chunking and summarizing to prevent context window overflow.
Used by skills that return large amounts of text (web_fetch, file reading, etc.)
"""

import re
from typing import Dict, List, Any, Optional
import asyncio


class ContentSummarizer:
    """
    Intelligent content summarization pipeline that:
    1. Detects content size and type
    2. Chunks large content intelligently
    3. Summarizes each chunk
    4. Aggregates summaries into final output
    """

    def __init__(self, max_chars: int = 50000, chunk_size: int = 8000):
        self.max_chars = max_chars  # Context window limit
        self.chunk_size = chunk_size  # Size per chunk for summarization
        self.client = None

    async def _get_client(self):
        """Lazy load OpenAI client"""
        if self.client is None:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI()
        return self.client

    def detect_content_type(self, text: str, headers: Dict[str, str] = None) -> str:
        """Detect content type for appropriate processing"""
        text_lower = text.lower()

        # Check headers first
        if headers:
            content_type = headers.get("content-type", "").lower()
            if "html" in content_type:
                return "html"
            elif "json" in content_type:
                return "json"
            elif "xml" in content_type:
                return "xml"

        # Fallback to content analysis
        if text_lower.strip().startswith("<!doctype html") or "<html" in text_lower:
            return "html"
        elif text_lower.strip().startswith("{") or text_lower.strip().startswith("["):
            return "json"
        elif text_lower.strip().startswith("<?xml") or "<xml" in text_lower:
            return "xml"
        else:
            return "text"

    def extract_html_content(self, html: str) -> Dict[str, str]:
        """Extract meaningful content from HTML"""
        content = {}

        # Extract title
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        content["title"] = title_match.group(1).strip() if title_match else ""

        # Extract meta description
        meta_desc = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html,
            re.IGNORECASE,
        )
        content["meta_description"] = meta_desc.group(1) if meta_desc else ""

        # Remove script and style tags
        clean_html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL
        )
        clean_html = re.sub(
            r"<style[^>]*>.*?</style>", "", clean_html, flags=re.IGNORECASE | re.DOTALL
        )

        # Extract text from common content tags
        content_patterns = [
            r"<main[^>]*>(.*?)</main>",
            r"<article[^>]*>(.*?)</article>",
            r"<section[^>]*>(.*?)</section>",
            r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
            r"<p[^>]*>(.*?)</p>",
        ]

        main_content = []
        for pattern in content_patterns:
            matches = re.findall(pattern, clean_html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Strip HTML tags
                text = re.sub(r"<[^>]+>", " ", match)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 50:  # Only include substantial content
                    main_content.append(text)

        content["main_text"] = " ".join(
            main_content[:10]
        )  # Limit to first 10 substantial paragraphs

        # Extract headings
        headings = re.findall(
            r"<h[1-6][^>]*>(.*?)</h[1-6]>", html, re.IGNORECASE | re.DOTALL
        )
        content["headings"] = [re.sub(r"<[^>]+>", "", h).strip() for h in headings[:20]]

        return content

    def intelligent_chunk(self, text: str, content_type: str) -> List[str]:
        """Chunk content intelligently based on type"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []

        if content_type == "html":
            # For HTML, try to chunk by sections/divs first
            section_pattern = (
                r"(<(?:section|article|div)[^>]*>.*?</(?:section|article|div)>)"
            )
            sections = re.findall(section_pattern, text, re.IGNORECASE | re.DOTALL)

            if sections:
                current_chunk = ""
                for section in sections:
                    if len(current_chunk) + len(section) > self.chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = section
                    else:
                        current_chunk += section
                if current_chunk:
                    chunks.append(current_chunk)
            else:
                # Fallback to paragraph chunking
                chunks = self._chunk_by_paragraphs(text)
        else:
            # For text, chunk by paragraphs or sentences
            chunks = self._chunk_by_paragraphs(text)

        return chunks

    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Chunk text by paragraphs, respecting size limits"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        # If chunks are still too large, split by sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks by sentences
                sentences = re.split(r"[.!?]+", chunk)
                current_sub_chunk = ""
                for sentence in sentences:
                    if len(current_sub_chunk) + len(sentence) > self.chunk_size:
                        if current_sub_chunk:
                            final_chunks.append(current_sub_chunk.strip())
                        current_sub_chunk = sentence
                    else:
                        current_sub_chunk += sentence + "."
                if current_sub_chunk:
                    final_chunks.append(current_sub_chunk.strip())

        return final_chunks

    async def summarize_chunk(
        self, chunk: str, content_type: str, context: str = ""
    ) -> str:
        """Summarize a single chunk of content"""
        client = await self._get_client()

        # Tailor prompt based on content type
        if content_type == "html":
            prompt = f"Summarize the key information from this webpage content. Focus on the main topics, important details, and useful information:\n\n{chunk}"
        elif content_type == "json":
            prompt = (
                f"Summarize the key data and structure from this JSON content:\n\n{chunk}"
            )
        else:
            prompt = f"Summarize the main points and important information from this text:\n\n{chunk}"

        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective for summaries
                messages=[
                    {
                        "role": "system",
                        "content": "You are a content summarizer. Create concise, informative summaries that capture the key points and important details. Be comprehensive but brief.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,  # Limit summary size
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            # Fallback to simple truncation if AI summarization fails
            return f"[Summary failed: {str(e)}] Content preview: {chunk[:500]}..."

    async def aggregate_summaries(
        self, summaries: List[str], original_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate multiple chunk summaries into final result"""
        if len(summaries) == 1:
            return {
                "summary": summaries[0],
                "chunk_count": 1,
                "processing_method": "single_summary",
            }

        # Combine summaries intelligently
        combined_text = "\n\n".join(
            [f"Section {i+1}: {summary}" for i, summary in enumerate(summaries)]
        )

        if len(combined_text) > self.chunk_size:
            # If combined summaries are still too long, summarize the summaries
            client = await self._get_client()

            try:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are synthesizing multiple content summaries into a comprehensive overview. Create a coherent, well-organized summary that captures all key information.",
                        },
                        {
                            "role": "user",
                            "content": f"Combine these section summaries into a comprehensive overview:\n\n{combined_text}",
                        },
                    ],
                    temperature=0.3,
                    max_tokens=1200,
                )

                final_summary = response.choices[0].message.content.strip()
            except Exception as e:
                final_summary = f"[Aggregation failed: {str(e)}] Combined summaries:\n\n{combined_text[:1000]}..."
        else:
            final_summary = combined_text

        return {
            "summary": final_summary,
            "chunk_count": len(summaries),
            "processing_method": "multi_chunk_summary",
            "original_size": original_context.get("original_size", 0),
        }

    async def process_content(
        self, text: str, headers: Dict[str, str] = None, context: str = ""
    ) -> Dict[str, Any]:
        """
        Main entry point: process large content with intelligent summarization

        Args:
            text: Content to process
            headers: HTTP headers for content type detection
            context: Additional context for summarization

        Returns:
            Dict with summary, metadata, and original content (if small enough)
        """
        original_size = len(text)

        # If content is small enough, return as-is
        if original_size <= self.max_chars:
            return {
                "content": text,
                "needs_processing": False,
                "original_size": original_size,
                "processing_method": "no_processing",
            }

        # Detect content type and extract structured info if possible
        content_type = self.detect_content_type(text, headers)

        extracted_info = {}
        if content_type == "html":
            extracted_info = self.extract_html_content(text)

        # Chunk content intelligently
        chunks = self.intelligent_chunk(text, content_type)

        # Summarize each chunk
        summaries = []
        for i, chunk in enumerate(chunks):
            chunk_context = (
                f"{context} (Part {i+1} of {len(chunks)})"
                if context
                else f"Part {i+1} of {len(chunks)}"
            )
            summary = await self.summarize_chunk(chunk, content_type, chunk_context)
            summaries.append(summary)

        # Aggregate summaries
        result = await self.aggregate_summaries(
            summaries, {"original_size": original_size}
        )

        # Add metadata
        result.update(
            {
                "needs_processing": True,
                "original_size": original_size,
                "content_type": content_type,
                "extracted_info": extracted_info,
                "truncated_preview": (
                    text[:1000] + "..." if original_size > 1000 else text
                ),
            }
        )

        return result


# Global summarizer instance
_summarizer = None


def get_summarizer() -> ContentSummarizer:
    """Get global summarizer instance"""
    global _summarizer
    if _summarizer is None:
        _summarizer = ContentSummarizer()
    return _summarizer


async def summarize_content(
    text: str, headers: Dict[str, str] = None, context: str = ""
) -> Dict[str, Any]:
    """Convenience function for content summarization"""
    summarizer = get_summarizer()
    return await summarizer.process_content(text, headers, context)
