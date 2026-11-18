"""
SQLAlchemy ORM models for the Chatbot Flow Builder PostgreSQL database.
Defines declarative mappings for Chatbots, Flows, and NodeDefinitions.
Uses JSONB for rich graph and schema documents, and timezone-aware timestamps.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    UUID,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def format_utc_iso(dt: Optional[datetime]) -> str:
    """Safely format datetime to UTC ISO 8601 string with +00:00 timezone."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


class Chatbot(Base):
    """
    Chatbot entity model.
    Represents an isolated chatbot configuration which groups multiple flows.
    """
    __tablename__ = "chatbots"

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    flows = relationship("Flow", back_populates="chatbot", passive_deletes=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary suitable for Pydantic serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class Flow(Base):
    """
    Flow entity model.
    Represents a conversation flow graph consisting of nodes and edges stored in JSONB.
    """
    __tablename__ = "flows"

    id = Column(String(100), primary_key=True, index=True)
    chatbot_id = Column(
        String(100),
        ForeignKey("chatbots.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    flow_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    chatbot = relationship("Chatbot", back_populates="flows")
    node_answers = relationship(
        "NodeAnswer",
        back_populates="flow",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary suitable for Pydantic serialization."""
        return {
            "id": self.id,
            "chatbot_id": self.chatbot_id,
            "name": self.name,
            "description": self.description,
            "flow_data": self.flow_data or {"nodes": [], "edges": []},
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class NodeDefinition(Base):
    """
    NodeDefinition entity model.
    Catalog of prebuilt and user-created custom node types for the flow builder canvas.
    """
    __tablename__ = "node_definitions"
    __table_args__ = (
        CheckConstraint(
            "node_source IN ('prebuilt', 'custom')",
            name="check_node_definition_source",
        ),
        Index("idx_node_definitions_filter", "is_active", "category", "node_source"),
    )

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    node_type = Column(String(50), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    node_source = Column(String(50), nullable=False)
    input_schema = Column(JSONB, nullable=False, default=dict)
    output_schema = Column(JSONB, nullable=False, default=dict)
    config_schema = Column(JSONB, nullable=False, default=dict)
    executor_type = Column(String(50), nullable=True)
    executor_config = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary suitable for Pydantic serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "category": self.category,
            "description": self.description,
            "node_source": self.node_source,
            "input_schema": self.input_schema or {},
            "output_schema": self.output_schema or {},
            "config_schema": self.config_schema or {},
            "executor_type": self.executor_type,
            "executor_config": self.executor_config or {},
            "is_active": bool(self.is_active),
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class NodeAnswer(Base):
    """
    NodeAnswer entity model.
    Stores multi-language answers associated with individual nodes in a flow.
    """
    __tablename__ = "node_answers"
    __table_args__ = (
        UniqueConstraint("flow_id", "node_id", "language", name="uq_node_answers_flow_node_lang"),
        Index("ix_node_answers_flow_id", "flow_id"),
        Index("ix_node_answers_node_id", "node_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    flow_id = Column(
        String(100),
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id = Column(String(255), nullable=False)
    language = Column(String(20), nullable=False, default="en", server_default="en")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    flow = relationship("Flow", back_populates="node_answers")
    answer_blocks = relationship(
        "AnswerBlock",
        back_populates="node_answer",
        cascade="all, delete-orphan",
        order_by="AnswerBlock.position",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "flow_id": self.flow_id,
            "node_id": self.node_id,
            "language": self.language,
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class MediaAsset(Base):
    """
    MediaAsset entity model.
    Stores metadata for uploaded media files (images, audio, video, pdfs)
    referenced by answer blocks.
    """
    __tablename__ = "media_assets"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    file_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False, unique=True, index=True)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(String(30), nullable=False)
    storage_key = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    answer_blocks = relationship("AnswerBlock", back_populates="media_asset")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "file_name": self.file_name,
            "stored_name": self.stored_name,
            "mime_type": self.mime_type,
            "media_type": self.media_type,
            "storage_key": self.storage_key,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "created_at": format_utc_iso(self.created_at),
        }


class AnswerBlock(Base):
    """
    AnswerBlock entity model.
    Represents an ordered block of content (text, image, video, pdf) within a node answer.
    """
    __tablename__ = "answer_blocks"
    __table_args__ = (
        CheckConstraint(
            "block_type IN ('text', 'image', 'video', 'pdf')",
            name="check_answer_block_type",
        ),
        Index("ix_answer_blocks_answer_id", "answer_id"),
        Index("ix_answer_blocks_media_id", "media_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    answer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("node_answers.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_type = Column(String(30), nullable=False)
    content = Column(Text, nullable=True)
    media_id = Column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    position = Column(Integer, nullable=False)
    block_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    node_answer = relationship("NodeAnswer", back_populates="answer_blocks")
    media_asset = relationship("MediaAsset", back_populates="answer_blocks")

    def __init__(self, **kwargs: Any) -> None:
        if "metadata" in kwargs and "block_metadata" not in kwargs:
            kwargs["block_metadata"] = kwargs.pop("metadata")
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "answer_id": str(self.answer_id) if self.answer_id else None,
            "block_type": self.block_type,
            "content": self.content,
            "media_id": str(self.media_id) if self.media_id else None,
            "position": self.position,
            "metadata": self.block_metadata,
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }

