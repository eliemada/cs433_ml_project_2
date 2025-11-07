"""RAG Pipeline for Academic Papers."""

__version__ = "0.1.0"
__author__ = "Elie Bruno"
__description__ = "RAG pipeline for academic papers with OpenAlex and Dolphin"

# Make key classes easily importable
from .openalex.fetcher import MetadataFetcher
from .openalex.downloader import PDFDownloader
from .parsing.model import DolphinModel
from .parsing.pdf_processor import PDFProcessor
from .rag.chunking import DocumentChunker
from .rag.openai_embedder import OpenAIEmbedder

__all__ = [
    "MetadataFetcher",
    "PDFDownloader",
    "DolphinModel",
    "PDFProcessor",
    "DocumentChunker",
    "OpenAIEmbedder",
]