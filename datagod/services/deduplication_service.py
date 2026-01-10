"""
Deduplication Service
Identifies and handles duplicate records across data sources

This service provides:
- Duplicate detection using fuzzy matching
- Multiple merge strategies (keep newest, keep most complete, manual)
- Batch deduplication for large datasets
- Audit trail for merged records
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json

from datagod.services.entity_linker import EntityLinker

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Strategies for merging duplicate records"""
    KEEP_NEWEST = "keep_newest"          # Keep the most recently updated record
    KEEP_OLDEST = "keep_oldest"          # Keep the original record
    KEEP_MOST_COMPLETE = "keep_complete" # Keep the record with most fields filled
    MERGE = "merge"                       # Combine non-conflicting fields
    MANUAL_REVIEW = "manual"             # Flag for manual review


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate records"""
    group_id: str
    records: List[Dict[str, Any]]
    confidence: float
    match_fields: List[str]
    recommended_strategy: MergeStrategy
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'group_id': self.group_id,
            'record_count': len(self.records),
            'record_ids': [r.get('record_id', r.get('id')) for r in self.records],
            'confidence': self.confidence,
            'match_fields': self.match_fields,
            'recommended_strategy': self.recommended_strategy.value,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class MergeResult:
    """Result of a merge operation"""
    success: bool
    kept_record: Optional[Dict[str, Any]]
    removed_records: List[str]
    strategy_used: MergeStrategy
    audit_info: Dict[str, Any]


class DeduplicationService:
    """
    Service for detecting and handling duplicate records.

    Features:
    - Configurable duplicate detection thresholds
    - Multiple merge strategies
    - Batch processing for large datasets
    - Full audit trail
    """

    # Default thresholds
    DEFAULT_DUPLICATE_THRESHOLD = 0.85
    DEFAULT_POSSIBLE_THRESHOLD = 0.70

    # Fields that indicate a likely duplicate if they match
    HIGH_WEIGHT_FIELDS = ['parcel_id', 'document_number', 'record_id', 'ssn', 'ein']
    MEDIUM_WEIGHT_FIELDS = ['property_address', 'grantor', 'grantee', 'owner_name']
    LOW_WEIGHT_FIELDS = ['record_date', 'amount', 'document_type']

    def __init__(self,
                 entity_linker: EntityLinker = None,
                 duplicate_threshold: float = None,
                 possible_threshold: float = None):
        """
        Initialize the DeduplicationService.

        Args:
            entity_linker: EntityLinker instance for fuzzy matching
            duplicate_threshold: Threshold for definite duplicates (default 0.85)
            possible_threshold: Threshold for possible duplicates (default 0.70)
        """
        self.entity_linker = entity_linker or EntityLinker()
        self.duplicate_threshold = duplicate_threshold or self.DEFAULT_DUPLICATE_THRESHOLD
        self.possible_threshold = possible_threshold or self.DEFAULT_POSSIBLE_THRESHOLD

        # Track processed groups
        self.duplicate_groups: Dict[str, DuplicateGroup] = {}
        self.merge_history: List[MergeResult] = []

        logger.info(f"DeduplicationService initialized with thresholds: "
                   f"duplicate={self.duplicate_threshold}, possible={self.possible_threshold}")

    def find_duplicates(self, record: Dict[str, Any],
                       candidates: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """
        Find potential duplicates of a record in a list of candidates.

        Args:
            record: Record to check for duplicates
            candidates: List of records to compare against

        Returns:
            List of DuplicateGroups containing potential duplicates
        """
        matches = []

        for candidate in candidates:
            # Skip if same record
            if self._get_record_id(record) == self._get_record_id(candidate):
                continue

            similarity, match_fields = self._calculate_similarity(record, candidate)

            if similarity >= self.possible_threshold:
                matches.append({
                    'record': candidate,
                    'similarity': similarity,
                    'match_fields': match_fields
                })

        if not matches:
            return []

        # Group by similarity
        definite_matches = [m for m in matches if m['similarity'] >= self.duplicate_threshold]
        possible_matches = [m for m in matches if self.possible_threshold <= m['similarity'] < self.duplicate_threshold]

        groups = []

        if definite_matches:
            all_records = [record] + [m['record'] for m in definite_matches]
            avg_similarity = sum(m['similarity'] for m in definite_matches) / len(definite_matches)
            all_match_fields = set()
            for m in definite_matches:
                all_match_fields.update(m['match_fields'])

            group = DuplicateGroup(
                group_id=self._generate_group_id(all_records),
                records=all_records,
                confidence=avg_similarity,
                match_fields=list(all_match_fields),
                recommended_strategy=MergeStrategy.KEEP_NEWEST
            )
            groups.append(group)

        if possible_matches:
            for match in possible_matches:
                group = DuplicateGroup(
                    group_id=self._generate_group_id([record, match['record']]),
                    records=[record, match['record']],
                    confidence=match['similarity'],
                    match_fields=match['match_fields'],
                    recommended_strategy=MergeStrategy.MANUAL_REVIEW
                )
                groups.append(group)

        return groups

    def find_all_duplicates(self, records: List[Dict[str, Any]],
                           progress_callback: Callable = None) -> List[DuplicateGroup]:
        """
        Find all duplicate groups in a list of records.

        Args:
            records: List of records to check
            progress_callback: Optional callback for progress updates

        Returns:
            List of DuplicateGroups
        """
        all_groups = []
        processed_ids = set()
        total = len(records)

        for i, record in enumerate(records):
            record_id = self._get_record_id(record)

            if record_id in processed_ids:
                continue

            # Find duplicates for this record
            remaining = records[i + 1:]
            groups = self.find_duplicates(record, remaining)

            for group in groups:
                # Mark all records in group as processed
                for r in group.records:
                    processed_ids.add(self._get_record_id(r))

                all_groups.append(group)
                self.duplicate_groups[group.group_id] = group

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)

        logger.info(f"Found {len(all_groups)} duplicate groups in {total} records")
        return all_groups

    def _calculate_similarity(self, record1: Dict[str, Any],
                             record2: Dict[str, Any]) -> tuple[float, List[str]]:
        """
        Calculate similarity between two records.

        Returns:
            Tuple of (similarity score, list of matching fields)
        """
        # Skip if same record (based on record_id)
        if self._get_record_id(record1) == self._get_record_id(record2):
            return 0.0, []

        match_fields = []
        scores = []
        weights = []

        # Check high-weight fields
        for field in self.HIGH_WEIGHT_FIELDS:
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field]).strip().lower()
                    val2 = str(record2[field]).strip().lower()
                    if val1 == val2:
                        scores.append(1.0)
                        weights.append(3.0)
                        match_fields.append(field)
                    else:
                        scores.append(0.0)
                        weights.append(3.0)

        # Check medium-weight fields with fuzzy matching
        for field in self.MEDIUM_WEIGHT_FIELDS:
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field])
                    val2 = str(record2[field])
                    similarity = self.entity_linker._jaro_winkler(
                        val1.lower().strip(),
                        val2.lower().strip()
                    )
                    scores.append(similarity)
                    weights.append(2.0)
                    if similarity > 0.85:
                        match_fields.append(field)

        # Check low-weight fields
        for field in self.LOW_WEIGHT_FIELDS:
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field]).strip().lower()
                    val2 = str(record2[field]).strip().lower()
                    if val1 == val2:
                        scores.append(1.0)
                        match_fields.append(field)
                    else:
                        scores.append(0.0)
                    weights.append(1.0)

        if not scores:
            return 0.0, []

        # Calculate weighted average
        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        return weighted_score, match_fields

    def merge_duplicates(self, group: DuplicateGroup,
                        strategy: MergeStrategy = None) -> MergeResult:
        """
        Merge a group of duplicate records.

        Args:
            group: DuplicateGroup to merge
            strategy: Merge strategy to use (default: use recommended)

        Returns:
            MergeResult with details of the merge
        """
        if not group.records or len(group.records) < 2:
            return MergeResult(
                success=False,
                kept_record=None,
                removed_records=[],
                strategy_used=strategy or group.recommended_strategy,
                audit_info={'error': 'Not enough records to merge'}
            )

        strategy = strategy or group.recommended_strategy

        if strategy == MergeStrategy.MANUAL_REVIEW:
            # Don't automatically merge, just mark for review
            return MergeResult(
                success=False,
                kept_record=None,
                removed_records=[],
                strategy_used=strategy,
                audit_info={'status': 'requires_manual_review', 'group_id': group.group_id}
            )

        # Select primary record based on strategy
        if strategy == MergeStrategy.KEEP_NEWEST:
            kept_record = self._select_newest(group.records)
        elif strategy == MergeStrategy.KEEP_OLDEST:
            kept_record = self._select_oldest(group.records)
        elif strategy == MergeStrategy.KEEP_MOST_COMPLETE:
            kept_record = self._select_most_complete(group.records)
        elif strategy == MergeStrategy.MERGE:
            kept_record = self._merge_records(group.records)
        else:
            kept_record = group.records[0]

        # Get list of removed record IDs
        kept_id = self._get_record_id(kept_record)
        removed_ids = [
            self._get_record_id(r) for r in group.records
            if self._get_record_id(r) != kept_id
        ]

        result = MergeResult(
            success=True,
            kept_record=kept_record,
            removed_records=removed_ids,
            strategy_used=strategy,
            audit_info={
                'group_id': group.group_id,
                'merged_at': datetime.now().isoformat(),
                'record_count': len(group.records),
                'confidence': group.confidence,
                'match_fields': group.match_fields,
            }
        )

        self.merge_history.append(result)

        logger.info(f"Merged {len(removed_ids)} records into {kept_id} using {strategy.value}")
        return result

    def _select_newest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the most recently updated record."""
        def get_date(r):
            for field in ['updated_at', 'created_at', 'record_date', 'fetched_at']:
                if field in r and r[field]:
                    try:
                        if isinstance(r[field], datetime):
                            return r[field]
                        return datetime.fromisoformat(str(r[field]).replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue
            return datetime.min

        return max(records, key=get_date)

    def _select_oldest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the oldest record."""
        def get_date(r):
            for field in ['created_at', 'record_date', 'fetched_at']:
                if field in r and r[field]:
                    try:
                        if isinstance(r[field], datetime):
                            return r[field]
                        return datetime.fromisoformat(str(r[field]).replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue
            return datetime.max

        return min(records, key=get_date)

    def _select_most_complete(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the record with the most non-empty fields."""
        def count_fields(r):
            return sum(1 for v in r.values() if v is not None and v != '' and v != [])

        return max(records, key=count_fields)

    def _merge_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple records, combining non-conflicting fields."""
        if not records:
            return {}

        # Start with the most complete record
        merged = self._select_most_complete(records).copy()

        # Add fields from other records if not present
        for record in records:
            for key, value in record.items():
                if key not in merged or not merged[key]:
                    if value is not None and value != '' and value != []:
                        merged[key] = value

        # Track merge sources
        merged['_merged_from'] = [self._get_record_id(r) for r in records]
        merged['_merged_at'] = datetime.now().isoformat()

        return merged

    def _get_record_id(self, record: Dict[str, Any]) -> str:
        """Get the ID of a record."""
        for field in ['record_id', 'id', 'document_id', '_id']:
            if field in record and record[field]:
                return str(record[field])

        # Generate hash-based ID if no ID field
        return hashlib.md5(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    def _generate_group_id(self, records: List[Dict[str, Any]]) -> str:
        """Generate a unique ID for a duplicate group."""
        record_ids = sorted([self._get_record_id(r) for r in records])
        combined = '-'.join(record_ids)
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def get_statistics(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        total_groups = len(self.duplicate_groups)
        total_merges = len(self.merge_history)
        successful_merges = sum(1 for m in self.merge_history if m.success)
        total_removed = sum(len(m.removed_records) for m in self.merge_history if m.success)

        strategy_counts = {}
        for merge in self.merge_history:
            strategy = merge.strategy_used.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        return {
            'total_duplicate_groups': total_groups,
            'total_merge_operations': total_merges,
            'successful_merges': successful_merges,
            'total_records_removed': total_removed,
            'merge_by_strategy': strategy_counts,
            'duplicate_threshold': self.duplicate_threshold,
            'possible_threshold': self.possible_threshold,
        }

    def get_pending_review(self) -> List[DuplicateGroup]:
        """Get duplicate groups pending manual review."""
        return [
            g for g in self.duplicate_groups.values()
            if g.recommended_strategy == MergeStrategy.MANUAL_REVIEW
        ]

    def clear_history(self):
        """Clear merge history and duplicate groups."""
        self.duplicate_groups.clear()
        self.merge_history.clear()
        logger.info("Cleared deduplication history")


# Convenience function
def deduplicate_records(records: List[Dict[str, Any]],
                       strategy: MergeStrategy = MergeStrategy.KEEP_NEWEST,
                       threshold: float = 0.85) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deduplicate a list of records.

    Args:
        records: List of records to deduplicate
        strategy: Merge strategy to use
        threshold: Similarity threshold for duplicates

    Returns:
        Tuple of (deduplicated records, statistics)
    """
    service = DeduplicationService(duplicate_threshold=threshold)

    # Find all duplicates
    groups = service.find_all_duplicates(records)

    # Process each group
    kept_ids = set()
    removed_ids = set()

    for group in groups:
        result = service.merge_duplicates(group, strategy)
        if result.success:
            kept_ids.add(service._get_record_id(result.kept_record))
            removed_ids.update(result.removed_records)

    # Filter to keep only non-removed records
    deduplicated = []
    for record in records:
        record_id = service._get_record_id(record)
        if record_id not in removed_ids:
            deduplicated.append(record)

    return deduplicated, service.get_statistics()
