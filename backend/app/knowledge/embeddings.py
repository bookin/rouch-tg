"""Text embeddings for Qdrant using Sentence Transformers"""
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Global model instance
_model = None
_executor = ThreadPoolExecutor(max_workers=1)
logger = logging.getLogger(__name__)

def _get_model():
    """Load model in a separate thread to avoid blocking"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            # Check for available device
            device = 'cpu'
            if torch.backends.mps.is_available():
                device = 'mps'
                logger.info("Using MPS (Apple Metal) for GPU acceleration")
            elif torch.cuda.is_available():
                device = 'cuda'
                logger.info("Using CUDA for GPU acceleration")
            else:
                logger.info("Using CPU for embeddings")
            
            # Use a lightweight multilingual model
            _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
            logger.info(f"Model loaded on device: {device}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}", exc_info=True)
            return None
    return _model

def _generate_embedding_sync(text: str) -> List[float]:
    """Generate embedding synchronously"""
    model = _get_model()
    if model:
        return model.encode(text).tolist()
    
    # Fallback to hash-based if model fails
    import hashlib
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()
    vector = []
    for i in range(384 // len(hash_bytes) + 1):  # 384 dimensions for MiniLM
        for byte in hash_bytes:
            if len(vector) < 384:
                vector.append((byte - 128) / 128.0)
    return vector[:384]

async def embed_text(text: str) -> List[float]:
    """
    Generate embedding vector for text using Sentence Transformers.
    Runs in a thread pool to be async-friendly.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _generate_embedding_sync, text)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch embed multiple texts"""
    loop = asyncio.get_running_loop()
    # Process in batches if needed, but for now simple list comprehension in executor
    return [await embed_text(text) for text in texts]
