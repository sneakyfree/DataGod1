"""Relationship model for DataGod"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from datagod.models.base import Base


class Relationship(Base):
    """
    Represents relationships between entities
    """

    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationship participants
    entity1_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    entity2_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    record_id = Column(Integer, ForeignKey("records.id"), nullable=False)

    # Relationship details
    relationship_type = Column(String(100), nullable=False)
    # Types: 'owner', 'lender', 'borrower', 'agent', 'buyer', 'seller', etc.
    role1 = Column(String(100), nullable=True)  # Entity1's role in the relationship
    role2 = Column(String(100), nullable=True)  # Entity2's role in the relationship

    # Context and evidence
    context = Column(Text, nullable=True)  # Description of the relationship context
    evidence = Column(JSON, nullable=True)  # Supporting evidence from records
    confidence_score = Column(
        Float, default=1.0
    )  # Confidence in the relationship (0.0 to 1.0)

    # Temporal information
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), default="active")
    # 'active', 'inactive', 'disputed'

    # Additional data
    relationship_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_relationship_entities", "entity1_id", "entity2_id"),
        Index("idx_relationship_record", "record_id"),
        Index("idx_relationship_type", "relationship_type"),
        Index("idx_relationship_status", "status"),
    )

    def __repr__(self):
        return f"<Relationship(id={self.id}, type='{self.relationship_type}', entities={self.entity1_id}-{self.entity2_id})>"
