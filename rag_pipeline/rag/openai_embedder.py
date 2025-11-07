"""
OpenAI embeddings generation module
"""

from openai import OpenAI
from typing import List, Dict, Optional
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """
    Generate embeddings using OpenAI's embedding models
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-large",
        dimensions: Optional[int] = None,
        batch_size: int = 100,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI embedder

        Args:
            api_key: OpenAI API key
            model: Embedding model to use
            dimensions: Output dimensions (if supported by model)
            batch_size: Number of texts to process at once
            max_retries: Maximum retry attempts for failed requests
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.max_retries = max_retries

        logger.info(f"Initialized OpenAI embedder with model: {model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            # Prepare request parameters
            params = {
                "model": self.model,
                "input": text
            }

            # Add dimensions if specified (for text-embedding-3 models)
            if self.dimensions and "text-embedding-3" in self.model:
                params["dimensions"] = self.dimensions

            # Generate embedding
            response = self.client.embeddings.create(**params)

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_embeddings_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress

        Returns:
            List of embedding vectors
        """
        try:
            all_embeddings = []

            # Process in batches
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]

                if show_progress:
                    logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1}")

                # Prepare request parameters
                params = {
                    "model": self.model,
                    "input": batch
                }

                if self.dimensions and "text-embedding-3" in self.model:
                    params["dimensions"] = self.dimensions

                # Generate embeddings
                response = self.client.embeddings.create(**params)

                # Extract embeddings
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                # Rate limiting
                time.sleep(0.1)

            logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def generate_chunks_with_embeddings(
        self,
        chunks: List[Dict[str, any]],
        text_field: str = "text"
    ) -> List[Dict[str, any]]:
        """
        Generate embeddings for a list of chunks

        Args:
            chunks: List of chunk dictionaries
            text_field: Field name containing text to embed

        Returns:
            Chunks with added 'embedding' field
        """
        try:
            # Extract texts
            texts = [chunk[text_field] for chunk in chunks]

            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts, show_progress=True)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding

            return chunks

        except Exception as e:
            logger.error(f"Error generating chunk embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for current model

        Returns:
            Embedding dimension
        """
        if self.dimensions:
            return self.dimensions

        # Default dimensions for known models
        dimensions_map = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536
        }

        return dimensions_map.get(self.model, 1536)

    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self.model)
            tokens = encoding.encode(text)
            return len(tokens)

        except Exception as e:
            # Fallback: rough estimation (4 chars per token)
            logger.warning(f"Could not calculate exact tokens: {e}")
            return len(text) // 4

    def calculate_cost(self, num_tokens: int) -> float:
        """
        Calculate estimated cost for embeddings

        Args:
            num_tokens: Number of tokens to process

        Returns:
            Estimated cost in USD
        """
        # Pricing as of 2024 (per 1M tokens)
        pricing_map = {
            "text-embedding-3-large": 0.13,
            "text-embedding-3-small": 0.02,
            "text-embedding-ada-002": 0.10
        }

        price_per_million = pricing_map.get(self.model, 0.10)
        cost = (num_tokens / 1_000_000) * price_per_million

        return cost
