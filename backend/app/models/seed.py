"""Seed and practice models"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import uuid4


class Seed(BaseModel):
    """Karmic seed planted by user"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Action details
    action_type: str  # 'giving', 'kindness', 'patience', 'effort', 'concentration', 'wisdom'
    description: str
    
    # Related partner
    partner_id: Optional[str] = None
    partner_group: str = "world"  # 'colleagues', 'clients', 'suppliers', 'world', or custom
    
    # Strength factors (from book)
    intention_score: int = Field(ge=1, le=10, default=5)  # How sincere
    emotion_level: int = Field(ge=1, le=10, default=5)  # Strength of emotion
    understanding: bool = False  # Done with understanding of mechanism
    
    # Maturation prediction
    estimated_maturation_days: int = 21  # 14-30 days typically
    strength_multiplier: float = 1.0  # Calculated from factors above
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


class Habit(BaseModel):
    """User's habit (instance of practice)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    practice_id: str
    
    # Schedule
    frequency: str = "daily"  # 'daily', 'weekly', 'custom'
    preferred_time: str = "morning"  # 'morning', 'afternoon', 'evening'
    duration: int = 30  # minutes
    
    # Tracking
    streak: int = 0
    last_completed: Optional[datetime] = None
    completion_rate: float = 0.0  # % of completions
    
    # User customizations
    user_restrictions: List[str] = Field(default_factory=list)
    is_active: bool = True
    
    class Config:
        from_attributes = True


class HabitCompletion(BaseModel):
    """Record of habit completion"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    habit_id: str
    user_id: int
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional details
    duration_actual: Optional[int] = None  # actual minutes
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True
