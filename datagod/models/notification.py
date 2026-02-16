"""
DataGod Notification Model
In-app notifications for anomalies, search results, payments, and system events
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON
from datetime import datetime

from datagod.models import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """In-app notification for a user."""

    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # 'search', 'anomaly', 'payment', 'security', 'system'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    read = Column(Boolean, default=False, index=True)
    data = Column(JSON, nullable=True)  # Additional context (e.g., record_id, anomaly_id)
    action_url = Column(String(500), nullable=True)  # Deep link URL
