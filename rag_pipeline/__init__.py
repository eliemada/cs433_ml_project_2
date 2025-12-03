"""RAG Pipeline for Academic Papers."""

__version__ = "0.1.0"
__author__ = "Elie Bruno"
__description__ = "RAG pipeline for academic papers with OpenAlex and Dolphin"

# Lazy imports to avoid pulling in heavy dependencies (PyTorch, PIL, etc.)
# when only using the API server
__all__ = [
    "MetadataFetcher",
    "PDFDownloader",
    "DolphinModel",
    "PDFParsingPipeline",
    "PDFParsingConfig",
    "DocumentChunker",
    "OpenAIEmbedder",
]

def __getattr__(name):
    """Lazy loading of heavy dependencies."""
    if name == "MetadataFetcher":
        from .openalex.fetcher import MetadataFetcher
        return MetadataFetcher
    elif name == "PDFDownloader":
        from .openalex.downloader import PDFDownloader
        return PDFDownloader
    elif name == "DolphinModel":
        from .pdf_parsing import DolphinModel
        return DolphinModel
    elif name == "PDFParsingPipeline":
        from .pdf_parsing import PDFParsingPipeline
        return PDFParsingPipeline
    elif name == "PDFParsingConfig":
        from .pdf_parsing import PDFParsingConfig
        return PDFParsingConfig
    elif name == "DocumentChunker":
        from .rag.chunking import DocumentChunker
        return DocumentChunker
    elif name == "OpenAIEmbedder":
        from .rag.openai_embedder import OpenAIEmbedder
        return OpenAIEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")