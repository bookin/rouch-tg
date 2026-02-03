"""
Initialize knowledge base in Qdrant
Run: python -m app.knowledge.init_knowledge
"""
import asyncio
from pathlib import Path
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.qdrant_client import QdrantKnowledgeBase
from app.config import get_settings


async def main():
    """Load knowledge base and index in Qdrant"""
    settings = get_settings()
    
    print("🔄 Loading knowledge base from terms/...")
    
    # 1. Load all files
    knowledge_path = Path(settings.KNOWLEDGE_BASE_PATH)
    if not knowledge_path.exists():
        print(f"❌ Knowledge base path not found: {knowledge_path}")
        print("   Make sure terms/ directory is mounted to data/knowledge_base/")
        return
    
    loader = KnowledgeLoader(knowledge_path)
    items = await loader.load_all()
    print(f"✅ Loaded {len(items)} knowledge items")
    
    # Print breakdown
    types = {}
    for item in items:
        types[item.type] = types.get(item.type, 0) + 1
    for item_type, count in types.items():
        print(f"   - {item_type}: {count}")
    
    # 2. Create collections in Qdrant
    print("\n🔄 Indexing in Qdrant...")
    qdrant = QdrantKnowledgeBase(settings.QDRANT_URL)
    await qdrant.index_knowledge(items)
    print("✅ Indexed in Qdrant")
    
    # 3. Test search
    print("\n🔄 Testing search...")
    test_results = await qdrant.search_correlation("нестабильные доходы", limit=1)
    if test_results:
        print(f"✅ Test search successful:")
        print(f"   Problem: {test_results[0].get('problem', 'N/A')}")
        print(f"   Solution: {test_results[0].get('solution', 'N/A')[:50]}...")
    else:
        print("⚠️  Test search returned no results")
    
    print("\n🎉 Knowledge base initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())
