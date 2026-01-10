"""
Cross-Source Validator

Validates consistency across multiple data sources.

Features:
- Cross-source field comparison
- Discrepancy detection
- Confidence scoring
- Record reconciliation
"""

import re
import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class DiscrepancyType(Enum):
    """Types of cross-source discrepancies"""
    VALUE_MISMATCH = "value_mismatch"       # Different values for same field
    MISSING_IN_SOURCE = "missing_in_source"  # Field present in one source only
    FORMAT_DIFFERENCE = "format_difference"  # Same value, different format
    DATE_DIFFERENCE = "date_difference"      # Dates differ by small amount
    CASE_DIFFERENCE = "case_difference"      # Same value, different case
    PRECISION_DIFFERENCE = "precision_diff"  # Numbers differ slightly


class DiscrepancySeverity(Enum):
    """Severity levels for discrepancies"""
    CRITICAL = "critical"  # Major inconsistency, needs resolution
    HIGH = "high"          # Significant difference
    MEDIUM = "medium"      # Notable difference
    LOW = "low"            # Minor difference
    INFO = "info"          # Informational only


@dataclass
class SourceDiscrepancy:
    """Represents a discrepancy between sources"""
    field: str
    discrepancy_type: DiscrepancyType
    severity: DiscrepancySeverity
    source1_name: str
    source1_value: Any
    source2_name: str
    source2_value: Any
    message: Optional[str] = None
    recommended_value: Optional[Any] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'field': self.field,
            'discrepancy_type': self.discrepancy_type.value,
            'severity': self.severity.value,
            'source1_name': self.source1_name,
            'source1_value': str(self.source1_value) if self.source1_value else None,
            'source2_name': self.source2_name,
            'source2_value': str(self.source2_value) if self.source2_value else None,
            'message': self.message,
            'recommended_value': str(self.recommended_value) if self.recommended_value else None,
            'confidence': self.confidence,
        }


@dataclass
class CrossSourceResult:
    """Result of cross-source validation"""
    is_consistent: bool = True
    discrepancies: List[SourceDiscrepancy] = field(default_factory=list)
    sources_compared: List[str] = field(default_factory=list)
    reconciled_record: Optional[Dict[str, Any]] = None
    consistency_score: float = 1.0

    def add_discrepancy(self, discrepancy: SourceDiscrepancy):
        """Add a discrepancy"""
        self.discrepancies.append(discrepancy)
        if discrepancy.severity in (DiscrepancySeverity.CRITICAL, DiscrepancySeverity.HIGH):
            self.is_consistent = False
        # Update consistency score
        severity_weights = {
            DiscrepancySeverity.CRITICAL: 0.3,
            DiscrepancySeverity.HIGH: 0.2,
            DiscrepancySeverity.MEDIUM: 0.1,
            DiscrepancySeverity.LOW: 0.05,
            DiscrepancySeverity.INFO: 0.01,
        }
        weight = severity_weights.get(discrepancy.severity, 0.1)
        self.consistency_score = max(0, self.consistency_score - weight)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_consistent': self.is_consistent,
            'consistency_score': round(self.consistency_score, 3),
            'discrepancy_count': len(self.discrepancies),
            'sources_compared': self.sources_compared,
            'discrepancies': [d.to_dict() for d in self.discrepancies],
            'reconciled_record': self.reconciled_record,
        }


class CrossSourceValidator:
    """
    Validates data consistency across multiple sources.

    Features:
    - Field-by-field comparison
    - Fuzzy matching for text fields
    - Date tolerance for timestamps
    - Numeric precision handling
    """

    # Fields that must match exactly
    EXACT_MATCH_FIELDS = {
        'parcel_id', 'document_number', 'case_number', 'entity_id',
        'ssn_last4', 'ein', 'state'
    }

    # Fields where minor differences are acceptable
    FUZZY_MATCH_FIELDS = {
        'address', 'owner_name', 'grantor', 'grantee', 'plaintiff',
        'defendant', 'entity_name', 'first_name', 'last_name'
    }

    # Numeric fields with tolerance
    NUMERIC_FIELDS = {
        'assessed_value', 'market_value', 'last_sale_price', 'consideration',
        'amount_claimed', 'judgment_amount', 'square_feet', 'lot_size',
        'bedrooms', 'bathrooms', 'latitude', 'longitude'
    }

    # Date fields
    DATE_FIELDS = {
        'last_sale_date', 'recording_date', 'filing_date', 'disposition_date',
        'formation_date', 'dissolution_date', 'date_of_birth'
    }

    def __init__(self,
                 date_tolerance_days: int = 7,
                 numeric_tolerance_percent: float = 0.05,
                 fuzzy_threshold: float = 0.85):
        """
        Initialize the validator.

        Args:
            date_tolerance_days: Days difference allowed for date matching
            numeric_tolerance_percent: Percentage difference allowed for numbers
            fuzzy_threshold: Similarity threshold for fuzzy matching (0-1)
        """
        self.date_tolerance = timedelta(days=date_tolerance_days)
        self.numeric_tolerance = numeric_tolerance_percent
        self.fuzzy_threshold = fuzzy_threshold

    def validate(self, records: List[Tuple[str, Dict[str, Any]]]) -> CrossSourceResult:
        """
        Validate consistency across multiple source records.

        Args:
            records: List of (source_name, record) tuples

        Returns:
            CrossSourceResult with discrepancies
        """
        if len(records) < 2:
            return CrossSourceResult(
                is_consistent=True,
                sources_compared=[name for name, _ in records]
            )

        result = CrossSourceResult(
            sources_compared=[name for name, _ in records]
        )

        # Get all fields across all records
        all_fields: Set[str] = set()
        for _, record in records:
            all_fields.update(record.keys())

        # Compare each pair of records
        for i, (source1_name, record1) in enumerate(records):
            for source2_name, record2 in records[i + 1:]:
                self._compare_records(
                    result,
                    source1_name, record1,
                    source2_name, record2,
                    all_fields
                )

        return result

    def _compare_records(self, result: CrossSourceResult,
                         source1_name: str, record1: Dict[str, Any],
                         source2_name: str, record2: Dict[str, Any],
                         all_fields: Set[str]):
        """Compare two records and add discrepancies to result"""

        for field in all_fields:
            value1 = record1.get(field)
            value2 = record2.get(field)

            # Skip if both are None
            if value1 is None and value2 is None:
                continue

            # Check for missing in one source
            if value1 is None or value2 is None:
                present_source = source1_name if value1 is not None else source2_name
                missing_source = source2_name if value1 is not None else source1_name
                present_value = value1 if value1 is not None else value2

                result.add_discrepancy(SourceDiscrepancy(
                    field=field,
                    discrepancy_type=DiscrepancyType.MISSING_IN_SOURCE,
                    severity=self._get_missing_severity(field),
                    source1_name=present_source,
                    source1_value=present_value,
                    source2_name=missing_source,
                    source2_value=None,
                    message=f"Field '{field}' missing in {missing_source}",
                    recommended_value=present_value,
                    confidence=0.7
                ))
                continue

            # Compare values based on field type
            discrepancy = self._compare_values(
                field, value1, value2, source1_name, source2_name
            )
            if discrepancy:
                result.add_discrepancy(discrepancy)

    def _compare_values(self, field: str, value1: Any, value2: Any,
                        source1_name: str, source2_name: str) -> Optional[SourceDiscrepancy]:
        """Compare two values and return discrepancy if any"""

        # Exact match fields
        if field in self.EXACT_MATCH_FIELDS:
            if str(value1).strip().upper() != str(value2).strip().upper():
                return SourceDiscrepancy(
                    field=field,
                    discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                    severity=DiscrepancySeverity.CRITICAL,
                    source1_name=source1_name,
                    source1_value=value1,
                    source2_name=source2_name,
                    source2_value=value2,
                    message=f"Critical field '{field}' has different values",
                    confidence=0.0
                )
            return None

        # Numeric fields
        if field in self.NUMERIC_FIELDS:
            return self._compare_numeric(field, value1, value2, source1_name, source2_name)

        # Date fields
        if field in self.DATE_FIELDS:
            return self._compare_dates(field, value1, value2, source1_name, source2_name)

        # Fuzzy match fields
        if field in self.FUZZY_MATCH_FIELDS:
            return self._compare_fuzzy(field, value1, value2, source1_name, source2_name)

        # Default: exact string comparison (case insensitive)
        str1 = str(value1).strip().lower()
        str2 = str(value2).strip().lower()

        if str1 == str2:
            return None

        # Check for case difference
        if str1.lower() == str2.lower():
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.CASE_DIFFERENCE,
                severity=DiscrepancySeverity.INFO,
                source1_name=source1_name,
                source1_value=value1,
                source2_name=source2_name,
                source2_value=value2,
                message=f"Field '{field}' differs only in case",
                recommended_value=value1,  # Prefer first source
                confidence=0.9
            )

        return SourceDiscrepancy(
            field=field,
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=DiscrepancySeverity.MEDIUM,
            source1_name=source1_name,
            source1_value=value1,
            source2_name=source2_name,
            source2_value=value2,
            message=f"Field '{field}' has different values",
            confidence=0.5
        )

    def _compare_numeric(self, field: str, value1: Any, value2: Any,
                         source1_name: str, source2_name: str) -> Optional[SourceDiscrepancy]:
        """Compare numeric values with tolerance"""
        try:
            num1 = float(value1)
            num2 = float(value2)

            if num1 == num2:
                return None

            # Calculate percentage difference
            if num1 != 0 and num2 != 0:
                diff_pct = abs(num1 - num2) / max(abs(num1), abs(num2))
            else:
                diff_pct = 1.0 if num1 != num2 else 0.0

            if diff_pct <= self.numeric_tolerance:
                return SourceDiscrepancy(
                    field=field,
                    discrepancy_type=DiscrepancyType.PRECISION_DIFFERENCE,
                    severity=DiscrepancySeverity.LOW,
                    source1_name=source1_name,
                    source1_value=num1,
                    source2_name=source2_name,
                    source2_value=num2,
                    message=f"Field '{field}' differs by {diff_pct:.1%}",
                    recommended_value=(num1 + num2) / 2,  # Average
                    confidence=0.8
                )

            # Significant difference
            severity = DiscrepancySeverity.HIGH if diff_pct > 0.2 else DiscrepancySeverity.MEDIUM
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                severity=severity,
                source1_name=source1_name,
                source1_value=num1,
                source2_name=source2_name,
                source2_value=num2,
                message=f"Field '{field}' differs by {diff_pct:.1%}",
                confidence=0.5
            )

        except (ValueError, TypeError):
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                severity=DiscrepancySeverity.HIGH,
                source1_name=source1_name,
                source1_value=value1,
                source2_name=source2_name,
                source2_value=value2,
                message=f"Field '{field}' has incompatible numeric values",
                confidence=0.3
            )

    def _compare_dates(self, field: str, value1: Any, value2: Any,
                       source1_name: str, source2_name: str) -> Optional[SourceDiscrepancy]:
        """Compare date values with tolerance"""
        date1 = self._parse_date(value1)
        date2 = self._parse_date(value2)

        if date1 is None or date2 is None:
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.FORMAT_DIFFERENCE,
                severity=DiscrepancySeverity.MEDIUM,
                source1_name=source1_name,
                source1_value=value1,
                source2_name=source2_name,
                source2_value=value2,
                message=f"Field '{field}' has unparseable date format",
                confidence=0.4
            )

        if date1 == date2:
            return None

        diff = abs((date1 - date2).days)

        if diff <= self.date_tolerance.days:
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.DATE_DIFFERENCE,
                severity=DiscrepancySeverity.LOW,
                source1_name=source1_name,
                source1_value=date1,
                source2_name=source2_name,
                source2_value=date2,
                message=f"Field '{field}' differs by {diff} days",
                recommended_value=max(date1, date2),  # Prefer more recent
                confidence=0.7
            )

        severity = DiscrepancySeverity.HIGH if diff > 365 else DiscrepancySeverity.MEDIUM
        return SourceDiscrepancy(
            field=field,
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=severity,
            source1_name=source1_name,
            source1_value=date1,
            source2_name=source2_name,
            source2_value=date2,
            message=f"Field '{field}' differs by {diff} days",
            confidence=0.4
        )

    def _compare_fuzzy(self, field: str, value1: Any, value2: Any,
                       source1_name: str, source2_name: str) -> Optional[SourceDiscrepancy]:
        """Compare text values with fuzzy matching"""
        str1 = self._normalize_text(str(value1))
        str2 = self._normalize_text(str(value2))

        if str1 == str2:
            return None

        similarity = self._calculate_similarity(str1, str2)

        if similarity >= self.fuzzy_threshold:
            return SourceDiscrepancy(
                field=field,
                discrepancy_type=DiscrepancyType.FORMAT_DIFFERENCE,
                severity=DiscrepancySeverity.LOW,
                source1_name=source1_name,
                source1_value=value1,
                source2_name=source2_name,
                source2_value=value2,
                message=f"Field '{field}' similar ({similarity:.0%} match)",
                recommended_value=value1,  # Prefer first source
                confidence=similarity
            )

        severity = DiscrepancySeverity.HIGH if similarity < 0.5 else DiscrepancySeverity.MEDIUM
        return SourceDiscrepancy(
            field=field,
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            severity=severity,
            source1_name=source1_name,
            source1_value=value1,
            source2_name=source2_name,
            source2_value=value2,
            message=f"Field '{field}' mismatch ({similarity:.0%} similarity)",
            confidence=similarity
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = text.lower().strip()
        # Remove common punctuation
        text = re.sub(r'[,.\-\'\"()]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate text similarity using Jaro-Winkler"""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0

        s1_matches = [False] * len1
        s2_matches = [False] * len2
        matches = 0
        transpositions = 0

        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        jaro = (matches / len1 + matches / len2 +
                (matches - transpositions / 2) / matches) / 3

        # Winkler modification
        prefix = 0
        for i in range(min(len1, len2, 4)):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break

        return jaro + prefix * 0.1 * (1 - jaro)

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value"""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    def _get_missing_severity(self, field: str) -> DiscrepancySeverity:
        """Get severity for a missing field"""
        if field in self.EXACT_MATCH_FIELDS:
            return DiscrepancySeverity.HIGH
        if field in self.NUMERIC_FIELDS:
            return DiscrepancySeverity.MEDIUM
        return DiscrepancySeverity.LOW

    def reconcile(self, records: List[Tuple[str, Dict[str, Any]]],
                  priority_order: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Reconcile records from multiple sources into a single record.

        Args:
            records: List of (source_name, record) tuples
            priority_order: List of source names in priority order

        Returns:
            Reconciled record
        """
        if not records:
            return {}

        if len(records) == 1:
            return records[0][1].copy()

        # Default priority: first source wins
        if priority_order is None:
            priority_order = [name for name, _ in records]

        # Create source lookup
        source_map = {name: record for name, record in records}

        # Get all fields
        all_fields: Set[str] = set()
        for _, record in records:
            all_fields.update(record.keys())

        # Build reconciled record
        result = {}
        for field in all_fields:
            # Use first non-None value in priority order
            for source_name in priority_order:
                if source_name in source_map:
                    value = source_map[source_name].get(field)
                    if value is not None:
                        result[field] = value
                        break

        return result

    def get_statistics(self, results: List[CrossSourceResult]) -> Dict[str, Any]:
        """Get cross-source validation statistics"""
        total = len(results)
        consistent = sum(1 for r in results if r.is_consistent)

        # Count discrepancies by type
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_field: Dict[str, int] = {}

        for result in results:
            for disc in result.discrepancies:
                by_type[disc.discrepancy_type.value] = by_type.get(disc.discrepancy_type.value, 0) + 1
                by_severity[disc.severity.value] = by_severity.get(disc.severity.value, 0) + 1
                by_field[disc.field] = by_field.get(disc.field, 0) + 1

        avg_score = sum(r.consistency_score for r in results) / total if total > 0 else 0

        return {
            'total_comparisons': total,
            'consistent_records': consistent,
            'inconsistent_records': total - consistent,
            'consistency_rate': consistent / total if total > 0 else 0,
            'average_consistency_score': round(avg_score, 3),
            'total_discrepancies': sum(len(r.discrepancies) for r in results),
            'discrepancies_by_type': by_type,
            'discrepancies_by_severity': by_severity,
            'discrepancies_by_field': by_field,
        }


# Convenience functions
def validate_cross_source(records: List[Tuple[str, Dict[str, Any]]]) -> CrossSourceResult:
    """Validate records from multiple sources"""
    validator = CrossSourceValidator()
    return validator.validate(records)


def reconcile_records(records: List[Tuple[str, Dict[str, Any]]],
                      priority_order: Optional[List[str]] = None) -> Dict[str, Any]:
    """Reconcile records from multiple sources"""
    validator = CrossSourceValidator()
    return validator.reconcile(records, priority_order)
