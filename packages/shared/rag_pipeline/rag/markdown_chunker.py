"""
Hybrid Semantic Chunking for Research Papers in Markdown

Implements a two-tiered chunking strategy:
- Coarse chunks (~2000 chars) for broad context retrieval
- Fine chunks (~200-400 chars) for precise snippet extraction

Follows ZeroEntropy's recommendations for RAG systems.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import tiktoken


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    chunk_id: str
    chunk_type: str  # "coarse" or "fine"
    paper_id: str
    paper_title: str
    section_hierarchy: List[str]  # e.g., ["Chapter 2", "2.1", "The Nature of Security"]
    char_start: int
    char_end: int
    chunk_index: int  # Position in document
    total_chunks: int  # Total chunks in document
    overlap_with_previous: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class MarkdownChunker:
    """Chunks markdown documents using hybrid semantic + size-constrained approach"""

    def __init__(
        self,
        coarse_target_size: int = 2000,
        coarse_max_size: int = 2500,
        fine_target_size: int = 300,
        fine_max_size: int = 450,
        coarse_overlap_pct: float = 0.10,
        fine_overlap_pct: float = 0.20,
        model_name: str = "text-embedding-3-small"
    ):
        """
        Initialize the chunker with size parameters.

        Args:
            coarse_target_size: Target size for coarse chunks in characters
            coarse_max_size: Maximum size before forcing split
            fine_target_size: Target size for fine chunks in characters
            fine_max_size: Maximum size before forcing split
            coarse_overlap_pct: Overlap percentage for coarse chunks (0.0-1.0)
            fine_overlap_pct: Overlap percentage for fine chunks (0.0-1.0)
            model_name: OpenAI model name for token counting
        """
        self.coarse_target_size = coarse_target_size
        self.coarse_max_size = coarse_max_size
        self.fine_target_size = fine_target_size
        self.fine_max_size = fine_max_size
        self.coarse_overlap_pct = coarse_overlap_pct
        self.fine_overlap_pct = fine_overlap_pct

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base if model not found
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def extract_hierarchy(self, markdown_text: str) -> List[Tuple[str, int, str]]:
        """
        Extract heading hierarchy from markdown.

        Returns:
            List of (heading_text, level, full_line) tuples
        """
        lines = markdown_text.split('\n')
        headings = []

        for i, line in enumerate(lines):
            # Match markdown headings (##, ###, etc.)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                heading_text = match.group(2).strip()
                headings.append((heading_text, level, i))

        return headings

    def split_into_sections(self, markdown_text: str) -> List[Dict]:
        """
        Split markdown into sections based on heading hierarchy.

        Returns:
            List of section dicts with {heading_hierarchy, text, char_start, char_end}
        """
        lines = markdown_text.split('\n')
        headings = self.extract_hierarchy(markdown_text)
        sections = []

        if not headings:
            # No headings, treat whole document as one section
            return [{
                'heading_hierarchy': ['Document'],
                'text': markdown_text,
                'char_start': 0,
                'char_end': len(markdown_text)
            }]

        # Build section hierarchy
        hierarchy_stack = []

        for i, (heading_text, level, line_num) in enumerate(headings):
            # Update hierarchy stack
            hierarchy_stack = [h for h in hierarchy_stack if h[1] < level]
            hierarchy_stack.append((heading_text, level))

            # Get text from this heading to next heading (or end)
            start_line = line_num
            end_line = headings[i + 1][2] if i + 1 < len(headings) else len(lines)

            section_text = '\n'.join(lines[start_line:end_line])

            # Calculate character positions
            char_start = sum(len(line) + 1 for line in lines[:start_line])
            char_end = char_start + len(section_text)

            sections.append({
                'heading_hierarchy': [h[0] for h in hierarchy_stack],
                'text': section_text,
                'char_start': char_start,
                'char_end': char_end
            })

        return sections

    def split_at_paragraph_boundary(self, text: str, max_size: int) -> List[str]:
        """
        Split text at paragraph boundaries when it exceeds max_size.

        Args:
            text: Text to split
            max_size: Maximum character size

        Returns:
            List of text chunks split at paragraph boundaries
        """
        if len(text) <= max_size:
            return [text]

        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\n+', text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # Clean up paragraph
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds max_size, start new chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > max_size:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def add_overlap(self, chunks: List[str], overlap_pct: float) -> List[str]:
        """
        Add overlapping text between consecutive chunks.

        Args:
            chunks: List of text chunks
            overlap_pct: Percentage of overlap (0.0-1.0)

        Returns:
            List of chunks with overlap added
        """
        if len(chunks) <= 1:
            return chunks

        overlapped = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk, no overlap from previous
                overlapped.append(chunk)
            else:
                # Add overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_size = int(len(prev_chunk) * overlap_pct)
                overlap_text = prev_chunk[-overlap_size:].lstrip()

                # Add overlap at the beginning
                new_chunk = overlap_text + "\n\n" + chunk
                overlapped.append(new_chunk)

        return overlapped

    def create_coarse_chunks(
        self,
        markdown_text: str,
        paper_id: str,
        paper_title: str
    ) -> List[Chunk]:
        """
        Create coarse chunks (~2000 chars) for broad context retrieval.

        Args:
            markdown_text: Full markdown document
            paper_id: Unique paper identifier
            paper_title: Paper title for metadata

        Returns:
            List of Chunk objects
        """
        # Clean markdown (remove page breaks, excessive whitespace)
        cleaned_text = re.sub(r'\n---+\n', '\n\n', markdown_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        # Split into sections by headings
        sections = self.split_into_sections(cleaned_text)

        # Process each section
        raw_chunks = []
        for section in sections:
            section_chunks = self.split_at_paragraph_boundary(
                section['text'],
                self.coarse_max_size
            )

            for chunk_text in section_chunks:
                raw_chunks.append({
                    'text': chunk_text,
                    'hierarchy': section['heading_hierarchy'],
                    'char_start': section['char_start']
                })

        # Add overlap
        chunk_texts = [c['text'] for c in raw_chunks]
        overlapped_texts = self.add_overlap(chunk_texts, self.coarse_overlap_pct)

        # Create Chunk objects
        chunks = []
        for i, (chunk_text, raw_chunk) in enumerate(zip(overlapped_texts, raw_chunks)):
            chunk = Chunk(
                text=chunk_text,
                chunk_id=f"{paper_id}_coarse_{i:04d}",
                chunk_type="coarse",
                paper_id=paper_id,
                paper_title=paper_title,
                section_hierarchy=raw_chunk['hierarchy'],
                char_start=raw_chunk['char_start'],
                char_end=raw_chunk['char_start'] + len(chunk_text),
                chunk_index=i,
                total_chunks=len(overlapped_texts),
                overlap_with_previous=(i > 0)
            )
            chunks.append(chunk)

        return chunks

    def create_fine_chunks(
        self,
        coarse_chunks: List[Chunk]
    ) -> List[Chunk]:
        """
        Create fine chunks (~200-400 chars) from coarse chunks.

        Args:
            coarse_chunks: List of coarse Chunk objects

        Returns:
            List of fine Chunk objects
        """
        fine_chunks = []
        global_index = 0

        for coarse_chunk in coarse_chunks:
            # Split coarse chunk into paragraphs
            paragraphs = re.split(r'\n\n+', coarse_chunk.text)

            # Group paragraphs to reach target size
            chunk_texts = []
            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # If adding this paragraph exceeds max_size, start new chunk
                if current_chunk and len(current_chunk) + len(para) + 2 > self.fine_max_size:
                    chunk_texts.append(current_chunk.strip())
                    current_chunk = para
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para

            # Add remaining chunk
            if current_chunk:
                chunk_texts.append(current_chunk.strip())

            # Add overlap
            overlapped_texts = self.add_overlap(chunk_texts, self.fine_overlap_pct)

            # Create fine Chunk objects
            for i, chunk_text in enumerate(overlapped_texts):
                fine_chunk = Chunk(
                    text=chunk_text,
                    chunk_id=f"{coarse_chunk.paper_id}_fine_{global_index:04d}",
                    chunk_type="fine",
                    paper_id=coarse_chunk.paper_id,
                    paper_title=coarse_chunk.paper_title,
                    section_hierarchy=coarse_chunk.section_hierarchy,
                    char_start=coarse_chunk.char_start,
                    char_end=coarse_chunk.char_start + len(chunk_text),
                    chunk_index=global_index,
                    total_chunks=0,  # Will update later
                    overlap_with_previous=(i > 0)
                )
                fine_chunks.append(fine_chunk)
                global_index += 1

        # Update total_chunks
        total = len(fine_chunks)
        for chunk in fine_chunks:
            chunk.total_chunks = total

        return fine_chunks

    def chunk_document(
        self,
        markdown_text: str,
        paper_id: str,
        paper_title: str,
        create_both_types: bool = True
    ) -> Dict[str, List[Chunk]]:
        """
        Main entry point: chunk a markdown document.

        Args:
            markdown_text: Full markdown document
            paper_id: Unique paper identifier
            paper_title: Paper title for metadata
            create_both_types: If True, create both coarse and fine chunks

        Returns:
            Dict with 'coarse' and 'fine' chunk lists
        """
        coarse_chunks = self.create_coarse_chunks(markdown_text, paper_id, paper_title)

        if create_both_types:
            fine_chunks = self.create_fine_chunks(coarse_chunks)
        else:
            fine_chunks = []

        return {
            'coarse': coarse_chunks,
            'fine': fine_chunks
        }

    def get_chunk_stats(self, chunks: List[Chunk]) -> Dict:
        """
        Calculate statistics for a list of chunks.

        Returns:
            Dict with stats (mean_length, median_length, etc.)
        """
        if not chunks:
            return {}

        lengths = [len(chunk.text) for chunk in chunks]
        token_counts = [len(self.tokenizer.encode(chunk.text)) for chunk in chunks]

        return {
            'count': len(chunks),
            'mean_chars': sum(lengths) / len(lengths),
            'median_chars': sorted(lengths)[len(lengths) // 2],
            'min_chars': min(lengths),
            'max_chars': max(lengths),
            'mean_tokens': sum(token_counts) / len(token_counts),
            'median_tokens': sorted(token_counts)[len(token_counts) // 2],
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
        }
