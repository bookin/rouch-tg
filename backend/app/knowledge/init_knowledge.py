"""
Initialize knowledge base in Qdrant
Run: python -m app.knowledge.init_knowledge
"""
import asyncio
from pathlib import Path
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.qdrant import QdrantKnowledgeBase
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
    types: dict[str, int] = {}
    for item in items:
        types[item.type] = types.get(item.type, 0) + 1
    for item_type, count in types.items():
        print(f"   - {item_type}: {count}")

    # Сопоставление типов KnowledgeItem с коллекциями Qdrant
    collection_counts = {
        "correlations": types.get("correlation", 0),
        "concepts": types.get("concept", 0),
        "quotes": types.get("quote", 0),
        "practices": types.get("practice", 0),
        "rules": types.get("rule", 0),
    }

    print("\n"); print("Collections to index in Qdrant:")
    for collection_name, count in collection_counts.items():
        if count:
            print(f"   - {collection_name}: {count} points")
        else:
            print(f"   - {collection_name}: 0 (will be recreated empty if collection exists)")
    
    # 2. Upsert practices into PracticeDB (canonical source)
    practice_items = [i for i in items if i.type == "practice"]
    if practice_items:
        print(f"\n🔄 Upserting {len(practice_items)} practices into PracticeDB...")
        await _upsert_practices_to_db(practice_items)
        print("✅ PracticeDB synced")

    # 3. Create collections in Qdrant
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


async def _upsert_practices_to_db(practice_items):
    """Upsert practices from KnowledgeItem list into PracticeDB."""
    from app.database import AsyncSessionLocal
    from app.models.db.practice import PracticeDB
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        for item in practice_items:
            meta = item.metadata
            pid = meta.get("id")
            if not pid:
                continue

            result = await db.execute(select(PracticeDB).where(PracticeDB.id == pid))
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = meta.get("name", existing.name)
                existing.category = meta.get("category", existing.category)
                existing.description = item.content
                existing.duration_minutes = meta.get("duration", existing.duration_minutes)
                existing.difficulty = meta.get("difficulty", 1)
                existing.physical_intensity = meta.get("physical_intensity", "low")
                existing.requires_morning = meta.get("requires_morning", False)
                existing.requires_silence = meta.get("requires_silence", False)
                existing.max_completions_per_day = meta.get("max_completions_per_day", 1)
                existing.habit_min_streak_days = meta.get("habit_min_streak_days", 14)
                existing.habit_min_score = meta.get("habit_min_score", 70)
                existing.steps = meta.get("steps", [])
                existing.contraindications = meta.get("contraindications", [])
                existing.benefits = meta.get("benefits", "")
                existing.tags = meta.get("tags", [])
                existing.source = "practices.csv"
            else:
                practice = PracticeDB(
                    id=pid,
                    name=meta.get("name", ""),
                    category=meta.get("category", ""),
                    description=item.content,
                    duration_minutes=meta.get("duration", 0),
                    difficulty=meta.get("difficulty", 1),
                    physical_intensity=meta.get("physical_intensity", "low"),
                    requires_morning=meta.get("requires_morning", False),
                    requires_silence=meta.get("requires_silence", False),
                    max_completions_per_day=meta.get("max_completions_per_day", 1),
                    habit_min_streak_days=meta.get("habit_min_streak_days", 14),
                    habit_min_score=meta.get("habit_min_score", 70),
                    steps=meta.get("steps", []),
                    contraindications=meta.get("contraindications", []),
                    benefits=meta.get("benefits", ""),
                    tags=meta.get("tags", []),
                    source="practices.csv",
                )
                db.add(practice)

        await db.commit()
        print(f"   Upserted {len(practice_items)} practices")


if __name__ == "__main__":
    asyncio.run(main())
