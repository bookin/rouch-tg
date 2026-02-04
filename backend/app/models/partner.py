"""Partner and partner group models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import uuid4


class PartnerGroup(BaseModel):
    """Group of partners (e.g., colleagues, clients, suppliers, world, custom)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    icon: str  # Emoji icon
    description: str
    is_default: bool = False  # True for 4 default groups
    user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)


# Default groups
DEFAULT_GROUPS = [
    {"name": "Коллеги", "icon": "👥", "description": "Сделать каждого героем", "is_default": True},
    {"name": "Клиенты", "icon": "🤝", "description": "Быть одержимым их успехом", "is_default": True},
    {"name": "Поставщики", "icon": "📦", "description": "Проявлять личный интерес", "is_default": True},
    {"name": "Мир", "icon": "🌍", "description": "Создавать ценность для всех", "is_default": True},
]


class Partner(BaseModel):
    """Individual partner within a group"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    group_id: str
    user_id: int
    
    # Jampa method - observing what they like
    preferences: List[str] = Field(default_factory=list)  # What they like/need
    important_dates: List[datetime] = Field(default_factory=list)  # Birthdays, etc.
    
    # Interaction history
    seeds_count: int = 0  # Number of seeds planted for them
    last_action_date: Optional[datetime] = None
    
    # Contact info
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)


class PartnerAction(BaseModel):
    """Action taken for a partner (for calendar and tracking)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    partner_id: str
    seed_id: Optional[str] = None  # Linked seed if applicable
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str  # Description of action taken
    
    model_config = ConfigDict(from_attributes=True)
