"""
Text chunking strategies for document processing
"""

from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


class DocumentChunker:
    """
    Split documents into chunks for embedding and retrieval
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize document chunker

        Args:
            chunk_size: Target size of each chunk in tokens/characters
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum size for a chunk
            separators: List of separators to use for splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.separators = separators or ["\n\n", "\n", ". ", " "]

    def semantic_chunking(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict[str, any]]:
        """
        Split text into semantic chunks (preserve paragraph/section boundaries)

        Args:
            text: Text to chunk
            metadata: Additional metadata to include in chunks

        Returns:
            List of chunk dictionaries
        """
        try:
            chunks = []

            # Split by paragraphs first
            paragraphs = text.split('\n\n')

            current_chunk = ""
            current_size = 0
            chunk_index = 0

            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue

                para_size = len(paragraph)

                # If paragraph alone exceeds chunk size, split it further
                if para_size > self.chunk_size * 1.5:
                    # Save current chunk if exists
                    if current_chunk:
                        chunks.append(self._create_chunk(
                            current_chunk.strip(),
                            chunk_index,
                            metadata
                        ))
                        chunk_index += 1
                        current_chunk = ""
                        current_size = 0

                    # Split long paragraph
                    sub_chunks = self._split_long_text(paragraph)
                    for sub_chunk in sub_chunks:
                        chunks.append(self._create_chunk(
                            sub_chunk,
                            chunk_index,
                            metadata
                        ))
                        chunk_index += 1

                # If adding paragraph exceeds chunk size, save current chunk
                elif current_size + para_size > self.chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk(
                            current_chunk.strip(),
                            chunk_index,
                            metadata
                        ))
                        chunk_index += 1

                    # Start new chunk with overlap
                    if self.chunk_overlap > 0:
                        overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                        current_chunk = overlap_text + "\n\n" + paragraph
                        current_size = len(overlap_text) + para_size
                    else:
                        current_chunk = paragraph
                        current_size = para_size
                else:
                    # Add paragraph to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                    current_size += para_size

            # Add final chunk
            if current_chunk and len(current_chunk) >= self.min_chunk_size:
                chunks.append(self._create_chunk(
                    current_chunk.strip(),
                    chunk_index,
                    metadata
                ))

            logger.info(f"Created {len(chunks)} chunks from text")
            return chunks

        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}")
            raise

    def fixed_size_chunking(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict[str, any]]:
        """
        Split text into fixed-size chunks

        Args:
            text: Text to chunk
            metadata: Additional metadata

        Returns:
            List of chunk dictionaries
        """
        try:
            chunks = []
            text_length = len(text)
            chunk_index = 0

            for i in range(0, text_length, self.chunk_size - self.chunk_overlap):
                chunk_text = text[i:i + self.chunk_size]

                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(
                        chunk_text,
                        chunk_index,
                        metadata
                    ))
                    chunk_index += 1

            logger.info(f"Created {len(chunks)} fixed-size chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in fixed-size chunking: {e}")
            raise

    def recursive_chunking(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict[str, any]]:
        """
        Recursively split text using different separators

        Args:
            text: Text to chunk
            metadata: Additional metadata

        Returns:
            List of chunk dictionaries
        """
        try:
            chunks = []
            splits = self._recursive_split(text, self.separators)

            chunk_index = 0
            current_chunk = ""

            for split in splits:
                if len(current_chunk) + len(split) > self.chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk(
                            current_chunk.strip(),
                            chunk_index,
                            metadata
                        ))
                        chunk_index += 1

                    current_chunk = split
                else:
                    current_chunk += split

            # Add final chunk
            if current_chunk and len(current_chunk) >= self.min_chunk_size:
                chunks.append(self._create_chunk(
                    current_chunk.strip(),
                    chunk_index,
                    metadata
                ))

            logger.info(f"Created {len(chunks)} recursive chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in recursive chunking: {e}")
            raise

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using separator hierarchy"""
        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        splits = text.split(separator)

        if len(splits) == 1:
            return self._recursive_split(text, remaining_separators)

        final_splits = []
        for split in splits:
            if len(split) > self.chunk_size:
                final_splits.extend(self._recursive_split(split, remaining_separators))
            else:
                final_splits.append(split + separator)

        return final_splits

    def _split_long_text(self, text: str) -> List[str]:
        """Split text that exceeds chunk size"""
        chunks = []

        # Try to split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get last N characters for overlap"""
        if len(text) <= overlap_size:
            return text

        # Try to find sentence boundary
        overlap_text = text[-overlap_size:]
        sentence_start = overlap_text.find('. ')

        if sentence_start != -1:
            return overlap_text[sentence_start + 2:]

        return overlap_text

    def _create_chunk(
        self,
        text: str,
        index: int,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Create chunk dictionary with metadata"""
        chunk = {
            "text": text,
            "chunk_index": index,
            "length": len(text),
            "word_count": len(text.split())
        }

        if metadata:
            chunk.update(metadata)

        return chunk

    def chunk_with_citations(
        self,
        text: str,
        citations: List[str],
        metadata: Optional[Dict] = None
    ) -> List[Dict[str, any]]:
        """
        Chunk text and associate citations with chunks

        Args:
            text: Text to chunk
            citations: List of citations found in text
            metadata: Additional metadata

        Returns:
            Chunks with citation associations
        """
        try:
            # Create chunks
            chunks = self.semantic_chunking(text, metadata)

            # Associate citations with chunks
            for chunk in chunks:
                chunk_citations = []
                chunk_text = chunk["text"]

                for citation in citations:
                    if citation in chunk_text:
                        chunk_citations.append(citation)

                chunk["citations"] = chunk_citations

            return chunks

        except Exception as e:
            logger.error(f"Error chunking with citations: {e}")
            raise
