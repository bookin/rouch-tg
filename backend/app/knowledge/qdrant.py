"""Qdrant vector database client"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.models.knowledge import KnowledgeItem
from .embeddings import embed_text
from app.config import get_settings
from app.knowledge.cache_decorator import cache_quote, cache_correlation
from datetime import datetime
import hashlib
import random
import uuid


class QdrantKnowledgeBase:
    """Manages knowledge base in Qdrant vector database"""
    
    def __init__(self, url: str):
        settings = get_settings()
        self.client = QdrantClient(url=url, api_key=settings.QDRANT_API_KEY)
        self.vector_size = settings.QDRANT_COLLECTION_SIZE
        
    async def index_knowledge(self, items: List[KnowledgeItem]):
        """Index all knowledge items into Qdrant collections"""
        
        # Group by type
        collections = {
            "correlations": [],
            "concepts": [],
            "quotes": [],
            "practices": [],
            "rules": []
        }
        
        for item in items:
            collection_name = item.type + "s"
            if collection_name in collections:
                collections[collection_name].append(item)
        
        # Create and populate each collection
        for collection_name, items_list in collections.items():
            if items_list:
                await self._create_collection(collection_name, items_list)
    
    async def _create_collection(self, name: str, items: List[KnowledgeItem]):
        """Create collection and add items"""
        
        # Recreate collection
        print(f"   → Recreating collection '{name}' in Qdrant...")
        try:
            self.client.delete_collection(collection_name=name)
            print(f"     • Deleted existing collection '{name}'")
        except Exception as e:
            # Часто это просто "collection not found" при первом запуске
            print(f"     • No existing collection '{name}' to delete or delete failed: {e}")
        
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
        )
        print(f"     • Created collection '{name}'")
        
        # Prepare points
        points = []
        for item in items:
            vector = await embed_text(item.content)
            
            points.append(PointStruct(
                id=self._point_id(item),
                vector=vector,
                payload={
                    "id": item.id,
                    "content": item.content,
                    "source": item.source,
                    "metadata": item.metadata
                }
            ))
        
        print(f"     • Prepared {len(points)} points to upload into '{name}'")
        
        # Upload in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=name,
                points=batch
            )
        print(f"     • Finished uploading {len(points)} points into '{name}'")
    
    def _point_id(self, item: KnowledgeItem) -> str:
        """
        Create a stable point id for Qdrant.

        Qdrant supports unsigned integers or UUIDs. We use uuid.uuid5 to generate
        a deterministic UUID from (type/source/content) to avoid collisions
        and make indexing repeatable.
        """
        base = f"{item.type}|{item.source}|{item.content}"
        return str(uuid.uuid5(uuid.NAMESPACE_OID, base))

    @cache_correlation()
    async def search_correlation(self, problem: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for solutions to a problem"""
        
        try:
            vector = await embed_text(problem)
            
            results = self.client.query_points(
                collection_name="correlations",
                query=vector,
                limit=limit
            )
            
            enriched_results: List[Dict[str, Any]] = []
            for hit in results.points:
                metadata = hit.payload.get("metadata") or {}
                enriched_results.append(
                    {
                        "problem": metadata.get("problem", ""),
                        "cause": metadata.get("cause", ""),
                        "solution": metadata.get("solution", ""),
                        # New structured fields (may be empty for старой таблицы):
                        "category": metadata.get("category", ""),
                        "sphere": metadata.get("sphere", ""),
                        "imprint": metadata.get("imprint", ""),
                        "quality": metadata.get("quality", ""),
                        "partners": metadata.get("partners", ""),
                        "principle": metadata.get("principle", ""),
                        "number": metadata.get("number", ""),
                        "problem_type": metadata.get("problem_type", ""),
                        "source_type": metadata.get("source_type", ""),
                        "score": hit.score,
                    }
                )
            
            return enriched_results
        except Exception as e:
            print(f"Error searching correlations: {e}")
            return []
    
    @cache_quote()
    async def get_daily_quote(self, focus_area: Optional[str] = None) -> Dict[str, Any]:
        """Get relevant quote for the day"""
        
        try:
            if focus_area:
                # Search by focus area
                vector = await embed_text(focus_area)
                results = self.client.query_points(
                    collection_name="quotes",
                    query=vector,
                    limit=1
                ).points
            else:
                # Deterministic "random" quote of the day without relying on Qdrant offsets
                points, _ = self.client.scroll(
                    collection_name="quotes",
                    limit=200,
                    with_payload=True,
                    with_vectors=False,
                )
                if points:
                    rng = random.Random(datetime.utcnow().strftime("%Y-%m-%d"))
                    point = rng.choice(points)
                    return {
                        "text": point.payload.get("content", ""),
                        "context": (point.payload.get("metadata") or {}).get("context"),
                        "source": point.payload.get("source"),
                    }
                results = []
            
            if results:
                return {
                    "text": results[0].payload["content"],
                    "context": results[0].payload["metadata"].get("context"),
                    "source": results[0].payload["source"]
                }
            
            return await self._get_fallback_quote()
            
        except Exception as e:
            print(f"Error getting quote: {e}")
            return await self._get_fallback_quote()
    
    async def search_practice(
        self, 
        need: str, 
        restrictions: Optional[List[str]] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for suitable practices"""
        
        try:
            vector = await embed_text(need)
            
            results = self.client.query_points(
                collection_name="practices",
                query=vector,
                limit=limit * 2  # Get more to filter
            ).points
            
            practices = []
            for hit in results:
                practice = {
                    "name": hit.payload["metadata"].get("name", ""),
                    "category": hit.payload["metadata"].get("category", ""),
                    "content": hit.payload["content"],
                    "duration": hit.payload["metadata"].get("duration", 30),
                    "score": hit.score
                }
                
                # Filter by restrictions
                if restrictions:
                    # Simple filtering - can be enhanced
                    if "back_pain" in restrictions and "прогиб" in practice["content"].lower():
                        continue
                
                practices.append(practice)
                
                if len(practices) >= limit:
                    break
            
            return practices
            
        except Exception as e:
            print(f"Error searching practices: {e}")
            return []
    
    async def search_rules(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for karmic management rules relevant to the query.

        Rules are stored in a separate "rules" collection, populated from karma-concepts.md.
        """
        try:
            vector = await embed_text(query)
            results = self.client.query_points(
                collection_name="rules",
                query=vector,
                limit=limit,
            )

            rules: List[Dict[str, Any]] = []
            for hit in results.points:
                payload = hit.payload or {}
                metadata = payload.get("metadata") or {}
                rules.append(
                    {
                        "number": metadata.get("number"),
                        "title": metadata.get("title", ""),
                        "content": payload.get("content", ""),
                        "source": payload.get("source", ""),
                        "score": hit.score,
                    }
                )

            return rules
        except Exception as e:
            print(f"Error searching rules: {e}")
            return []
    
    async def search_concepts(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for concepts"""
        
        try:
            vector = await embed_text(query)
            
            results = self.client.query_points(
                collection_name="concepts",
                query=vector,
                limit=limit
            )
            
            return [
                {
                    "title": hit.payload["metadata"].get("title", ""),
                    "content": hit.payload["content"],
                    "category": hit.payload["metadata"].get("category", ""),
                    "source": hit.payload["source"],
                    "score": hit.score
                }
                for hit in results.points
            ]
            
        except Exception as e:
            print(f"Error searching concepts: {e}")
            return []
    
    async def _get_fallback_quote(self) -> Dict[str, Any]:
        """Fallback quote if search fails"""
        return {
            "text": "Даяние приносит богатство, но не размер суммы важен, а щедрое состояние ума",
            "context": "О богатстве",
            "source": "diamond-concepts.md"
        }
