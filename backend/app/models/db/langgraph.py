"""LangGraph checkpoint tables."""
from __future__ import annotations

from sqlalchemy import Column, Integer, LargeBinary, PrimaryKeyConstraint, String

from app.database import Base


class LangGraphCheckpointDB(Base):
    """LangGraph checkpoints"""
    __tablename__ = "checkpoints"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id"),
        {"extend_existing": True}
    )

    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    parent_checkpoint_id = Column(String, nullable=True)
    type = Column(String, nullable=True)
    checkpoint = Column(LargeBinary, nullable=False)
    metadata_ = Column("metadata", LargeBinary, nullable=False)


class LangGraphCheckpointBlobDB(Base):
    """LangGraph checkpoint blobs"""
    __tablename__ = "checkpoint_blobs"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id", "type"),
        {"extend_existing": True}
    )

    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    blob = Column(LargeBinary, nullable=False)


class LangGraphCheckpointWriteDB(Base):
    """LangGraph checkpoint writes"""
    __tablename__ = "checkpoint_writes"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "checkpoint_id", "task_id", "idx"),
        {"extend_existing": True}
    )

    thread_id = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    task_id = Column(String, nullable=False)
    idx = Column(Integer, nullable=False)
    channel = Column(String, nullable=False)
    type = Column(String, nullable=True)
    blob = Column(LargeBinary, nullable=False)
