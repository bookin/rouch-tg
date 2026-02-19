"""Partner and partner group models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, UTC
from uuid import uuid4


class PartnerGroup(BaseModel):
    """Group of partners (e.g., source, ally, protege, world, custom)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    icon: str  # Emoji icon
    description: str
    universal_category: str = "world" # source, ally, protege, world
    is_default: bool = False  # True for 4 default groups
    user_id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(from_attributes=True)


# Default groups
DEFAULT_GROUPS = [
    {"name": "Соратник", "icon": "🤝", "description": "Кто помогает в делах (Коллеги, партнеры)", "universal_category": "ally", "is_default": True},
    {"name": "Подопечный", "icon": "🌱", "description": "Кто зависит от тебя (Клиенты, дети, подчиненные)", "universal_category": "protege", "is_default": True},
    {"name": "Источник", "icon": "🌳", "description": "Кто дает ресурсы (Родители, учителя, поставщики)", "universal_category": "source", "is_default": True},
    {"name": "Внешний мир", "icon": "🌍", "description": "Незнакомцы, конкуренты, общество", "universal_category": "world", "is_default": True},
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
    contact_type: str = "physical"  # physical, online, mental
    
    # Notes
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(from_attributes=True)


class PartnerAction(BaseModel):
    """Action taken for a partner (for calendar and tracking)"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    partner_id: str
    seed_id: Optional[str] = None  # Linked seed if applicable
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action: str  # Description of action taken
    
    model_config = ConfigDict(from_attributes=True)
