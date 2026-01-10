"""Jurisdiction model for DataGod"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from datagod.models.base import Base

class Jurisdiction(Base):
    """
    Represents a geographic jurisdiction (county, city, state, etc.)
    """
    __tablename__ = 'jurisdictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    state = Column(String(2), nullable=True, index=True)
    county = Column(String(100), nullable=True, index=True)
    type = Column(String(50), nullable=True)  # 'county', 'city', 'state', etc.
    api_available = Column(Boolean, default=False)
    scraper_needed = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    data_sources = relationship("DataSource", back_populates="jurisdiction")
    records = relationship("Record", back_populates="jurisdiction")
    
    # Indexes
    __table_args__ = (
        Index('idx_jurisdiction_state_county', 'state', 'county'),
    )
    
    def __repr__(self):
        return f"<Jurisdiction(name='{self.name}', state='{self.state}')>"
