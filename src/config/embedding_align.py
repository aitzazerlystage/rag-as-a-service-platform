"""Resize embedding vectors to match the Pinecone index dimension."""

from typing import List


def align_vector_to_index(vector: List[float], index_dimensions: int) -> List[float]:
    """
    Pad or truncate a vector so it matches the vector DB index size.
    nomic-embed-text outputs 768 dims; our Pinecone index uses 1024.
    """
    n = len(vector)
    if n == index_dimensions:
        return vector
    if n > index_dimensions:
        return vector[:index_dimensions]
    return vector + [0.0] * (index_dimensions - n)
