"""
DataGod Services

This package contains service modules for the DataGod platform.
"""

from .email_service import EmailService, get_email_service, configure_email_service
from .entity_linker import EntityLinker, Entity, EntityType, EntityMatch
from .deduplication_service import (
    DeduplicationService,
    MergeStrategy,
    DuplicateGroup,
    MergeResult,
    deduplicate_records
)

__all__ = [
    # Email service
    'EmailService',
    'get_email_service',
    'configure_email_service',
    # Entity linking
    'EntityLinker',
    'Entity',
    'EntityType',
    'EntityMatch',
    # Deduplication
    'DeduplicationService',
    'MergeStrategy',
    'DuplicateGroup',
    'MergeResult',
    'deduplicate_records',
]
