"""
DataGod Comment Model
Supports threaded comments on records and entities
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from datagod.models import Base, TimestampMixin


class Comment(Base, TimestampMixin):
    """Comment on a record or entity. Supports threading via parent_id."""

    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    record_id = Column(Integer, ForeignKey('records.id'), nullable=True, index=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey('comments.id'), nullable=True, index=True)
    text = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    replies = relationship("Comment", backref="parent", remote_side=[id], lazy="dynamic")
