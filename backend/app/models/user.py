"""User models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class UserProfile(BaseModel):
    """User profile with onboarding data and progress tracking"""
    
    id: int
    telegram_id: int
    first_name: str
    username: Optional[str] = None
    
    # Onboarding data
    occupation: str = "employee"  # 'entrepreneur', 'employee', 'freelancer'
    available_times: List[str] = Field(default_factory=list)  # ['morning', 'evening']
    daily_minutes: int = 30  # 10, 30, 60
    current_habits: List[str] = Field(default_factory=list)
    physical_restrictions: Optional[str] = None
    
    # Progress tracking
    streak_days: int = 0
    total_seeds: int = 0
    completed_practices: int = 0
    
    # Settings
    timezone: str = "UTC"
    morning_enabled: bool = True
    evening_enabled: bool = True
    current_focus: Optional[str] = None  # Current problem area
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_onboarding_update: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class OnboardingState(BaseModel):
    """Onboarding state for LangGraph workflow"""
    
    user_id: int
    telegram_id: int
    step: str = "intro"  # 'intro', 'schedule', 'habits', 'problems', 'partners', 'summary'
    data: dict = Field(default_factory=dict)
    completed: bool = False
    
    model_config = ConfigDict(from_attributes=True)
