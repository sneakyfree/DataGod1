"""Entity model for DataGod"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from datagod.models.base import Base


class Entity(Base):
    """
    Represents entities mentioned in records (people, companies, properties)
    """

    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    # Types: 'person', 'company', 'property', 'government'
    entity_id = Column(
        String(255), nullable=True, index=True
    )  # External ID if available

    # Contact information
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    # Business information
    business_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    incorporation_date = Column(DateTime, nullable=True)

    # Person information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)

    # Property information
    property_type = Column(String(50), nullable=True)
    parcel_id = Column(String(100), nullable=True)

    # Status and verification
    status = Column(String(50), default="active")
    # 'active', 'inactive', 'verified', 'unverified'
    verification_date = Column(DateTime, nullable=True)
    verification_source = Column(String(255), nullable=True)

    # Additional data
    description = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)  # Additional structured data
    entity_metadata = Column(JSON, nullable=True)  # Additional metadata

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_entity_name_type", "entity_name", "entity_type"),
        Index("idx_entity_id", "entity_id"),
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_city_state", "city", "state"),
    )

    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.entity_name}', type='{self.entity_type}')>"
