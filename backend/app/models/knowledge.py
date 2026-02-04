"""Knowledge base models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import uuid4


class KnowledgeItem(BaseModel):
    """Base knowledge item from terms/"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # 'concept', 'correlation', 'quote', 'practice', 'rule'
    content: str
    source: str  # Source file name
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


class Correlation(BaseModel):
    """Problem-solution correlation from diamond-correlations-table.md"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    problem: str
    cause: str  # Karmic cause
    solution: str  # What to do
    category: str  # 'finance', 'relationships', 'health', etc.
    principle: Optional[str] = None
    source: str = "diamond-correlations-table.md"
    
    model_config = ConfigDict(from_attributes=True)


class Quote(BaseModel):
    """Inspirational quote from books"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    author: Optional[str] = None
    context: Optional[str] = None  # About what
    tags: list = Field(default_factory=list)  # For searching
    source: str
    
    model_config = ConfigDict(from_attributes=True)


class Concept(BaseModel):
    """Core concept from the teachings"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    content: str
    category: str  # 'emptiness', 'imprints', 'correlations', etc.
    source: str
    
    model_config = ConfigDict(from_attributes=True)
