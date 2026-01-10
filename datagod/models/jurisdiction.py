"""Jurisdiction model for DataGod"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Index, JSON
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
    population = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # FIPS code support for standardized county identification
    fips_code = Column(String(5), nullable=True, index=True)  # Full 5-digit FIPS (state + county)
    state_fips = Column(String(2), nullable=True, index=True)  # 2-digit state FIPS
    county_fips = Column(String(3), nullable=True, index=True)  # 3-digit county FIPS
    county_seat = Column(String(100), nullable=True)  # County seat city name

    # Coverage tracking metadata (JSON field for flexible storage)
    jurisdiction_metadata = Column(JSON, nullable=True, default=dict)  # Stores coverage info per data category

    # Relationships
    data_sources = relationship("DataSource", back_populates="jurisdiction")
    records = relationship("Record", back_populates="jurisdiction")

    # Indexes
    __table_args__ = (
        Index('idx_jurisdiction_state_county', 'state', 'county'),
        Index('idx_jurisdiction_fips', 'fips_code'),
        Index('idx_jurisdiction_state_fips', 'state_fips'),
    )

    def __repr__(self):
        return f"<Jurisdiction(name='{self.name}', state='{self.state}', fips='{self.fips_code}')>"
