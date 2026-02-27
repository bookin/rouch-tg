"""Seed and practice models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, UTC
from uuid import uuid4


# Centralized action types for karmic seeds
ACTION_TYPES: dict[str, str] = {
    "giving": "Тёплое щедрое действие для блага другого человека",
    "kindness": "Этичный, добрый поступок, который бережно относится к другим",
    "patience": "Терпение и устойчивость, когда что-то идёт не так, как хочется",
    "effort": "Осознанное усилие и настойчивость в правильном направлении",
    "concentration": "Собранность внимания и присутствие в моменте",
    "wisdom": "Мудрое решение или взгляд, который помогает видеть корень ситуации",
}


class Seed(BaseModel):
    """Karmic seed planted by user"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Action details
    action_type: str  # 'giving', 'kindness', 'patience', 'effort', 'concentration', 'wisdom'
    description: str
    
    # Related partner
    partner_id: Optional[str] = None
    partner_group: str = "world"  # 'source', 'ally', 'protege', 'world', or custom
    
    # Strength factors (from book)
    intention_score: int = Field(ge=1, le=10, default=5)  # How sincere
    emotion_level: int = Field(ge=1, le=10, default=5)  # Strength of emotion
    understanding: bool = False  # Done with understanding of mechanism
    
    # Maturation prediction
    estimated_maturation_days: int = 21  # 14-30 days typically
    strength_multiplier: float = 1.0  # Calculated from factors above
    
    # Context links
    karma_plan_id: Optional[str] = None
    daily_plan_id: Optional[str] = None
    daily_task_id: Optional[int] = None
    practice_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Practice(BaseModel):
    """Practice template (yoga, meditation, etc.)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: str  # 'meditation', 'yoga', 'ethics', 'reflection'
    description: Optional[str] = None
    
    # Requirements
    duration_minutes: int
    requires_morning: bool = False
    requires_silence: bool = False
    physical_intensity: str = "low"  # 'low', 'medium', 'high'
    
    # From knowledge base
    source: Optional[str] = None  # e.g., 'yoga-concepts.md'
    
    model_config = ConfigDict(from_attributes=True)


