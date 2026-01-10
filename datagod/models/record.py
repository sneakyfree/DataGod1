"""Record model for DataGod"""

from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from datagod.models.base import Base

class Record(Base):
    """
    Represents a public record (mortgage, deed, lien, etc.)
    """
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    date = Column(Date, nullable=True)
    url = Column(String(1000), nullable=True)
    data = Column(JSON, nullable=True)  # Additional structured data
    record_type = Column(String(100), nullable=True)  # 'mortgage', 'deed', 'lien', etc.
    status = Column(String(50), default='active')  # 'active', 'archived', 'deleted'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="records")
    data_source = relationship("DataSource", back_populates="records")
    
    # Indexes
    __table_args__ = (
        Index('idx_record_jurisdiction', 'jurisdiction_id'),
        Index('idx_record_data_source', 'data_source_id'),
        Index('idx_record_date', 'date'),
        Index('idx_record_type', 'record_type'),
    )
    
    def __repr__(self):
        return f"<Record(title='{self.title}', amount={self.amount})>"
