"""DataSource model for DataGod"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from datagod.models.base import Base

class DataSource(Base):
    """
    Represents a data source for a jurisdiction (API endpoint, scraper target, etc.)
    """
    __tablename__ = 'data_sources'

    id = Column(Integer, primary_key=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'api', 'scraper', 'manual'
    url = Column(String(1024), nullable=True)
    api_endpoint = Column(String(500), nullable=True)
    status = Column(String(50), default='active')  # 'active', 'inactive', 'error'
    last_scraped = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="data_sources")
    records = relationship("Record", back_populates="data_source")
    
    # Indexes
    __table_args__ = (
        Index('idx_data_source_jurisdiction', 'jurisdiction_id'),
        Index('idx_data_source_status', 'status'),
    )
    
    def __repr__(self):
        return f"<DataSource(name='{self.name}', url='{self.url}')>"
