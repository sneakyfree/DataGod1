"""
DataGod Services

This package contains service modules for the DataGod platform.
"""

from .deduplication_service import (
    DeduplicationService,
    DuplicateGroup,
    MergeResult,
    MergeStrategy,
    deduplicate_records,
)
from .email_service import EmailService, configure_email_service, get_email_service
from .entity_linker import Entity, EntityLinker, EntityMatch, EntityType

__all__ = [
    # Email service
    "EmailService",
    "get_email_service",
    "configure_email_service",
    # Entity linking
    "EntityLinker",
    "Entity",
    "EntityType",
    "EntityMatch",
    # Deduplication
    "DeduplicationService",
    "MergeStrategy",
    "DuplicateGroup",
    "MergeResult",
    "deduplicate_records",
]
