"""
Data Deduplication System
Implements Task 4.4 of the Master Plan
Provides comprehensive duplicate detection and merging capabilities
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate records"""

    group_id: str
    canonical_record: Dict[str, Any]
    duplicate_records: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    merge_strategy: str = "keep_canonical"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_records(self) -> int:
        return len(self.duplicate_records) + 1

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_records)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "canonical_record": self.canonical_record,
            "duplicate_records": self.duplicate_records,
            "confidence_score": self.confidence_score,
            "merge_strategy": self.merge_strategy,
            "total_records": self.total_records,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class DeduplicationMetrics:
    """Metrics for deduplication operations"""

    total_records_processed: int = 0
    duplicates_found: int = 0
    duplicate_groups_created: int = 0
    records_merged: int = 0
    records_deleted: int = 0
    processing_time_seconds: float = 0.0
    similarity_threshold: float = 0.8
    algorithm_used: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records_processed": self.total_records_processed,
            "duplicates_found": self.duplicates_found,
            "duplicate_groups_created": self.duplicate_groups_created,
            "records_merged": self.records_merged,
            "records_deleted": self.records_deleted,
            "processing_time_seconds": self.processing_time_seconds,
            "similarity_threshold": self.similarity_threshold,
            "algorithm_used": self.algorithm_used,
            "deduplication_rate": (
                self.duplicates_found / max(1, self.total_records_processed) * 100
            ),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class DataNormalizer:
    """Normalizes data for better deduplication matching"""

    def __init__(self):
        # Common abbreviations and their expansions
        self.name_abbreviations = {
            "jr": "junior",
            "sr": "senior",
            "dr": "doctor",
            "mr": "mister",
            "mrs": "misses",
            "ms": "miss",
            "inc": "incorporated",
            "corp": "corporation",
            "llc": "limited liability company",
            "ltd": "limited",
            "co": "company",
            "assn": "association",
        }

        # Street address abbreviations
        self.street_abbreviations = {
            "st": "street",
            "ave": "avenue",
            "blvd": "boulevard",
            "rd": "road",
            "ln": "lane",
            "dr": "drive",
            "ct": "court",
            "pl": "place",
            "sq": "square",
            "cir": "circle",
        }

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove punctuation except for important separators
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Expand common abbreviations
        words = normalized.split()
        expanded_words = []

        for word in words:
            # Check for name abbreviations
            if word in self.name_abbreviations:
                expanded_words.append(self.name_abbreviations[word])
            # Check for street abbreviations
            elif word in self.street_abbreviations:
                expanded_words.append(self.street_abbreviations[word])
            else:
                expanded_words.append(word)

        return " ".join(expanded_words)

    def normalize_address(self, address: str) -> str:
        """Normalize address for comparison"""
        if not address:
            return ""

        # Normalize base text
        normalized = self.normalize_text(address)

        # Standardize common address patterns
        # Remove unit/apt numbers for matching
        normalized = re.sub(r"\b(apt|apartment|unit|suite)\s*\w+\b", "", normalized)
        normalized = re.sub(r"#\w+", "", normalized)

        # Normalize street numbers
        normalized = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", normalized)

        return normalized.strip()

    def normalize_name(self, name: str) -> str:
        """Normalize person/company name"""
        if not name:
            return ""

        normalized = self.normalize_text(name)

        # Remove common suffixes for matching
        suffixes = ["jr", "sr", "ii", "iii", "iv", "v", "phd", "md", "esq"]
        words = normalized.split()
        filtered_words = [w for w in words if w not in suffixes]

        return " ".join(filtered_words)

    def normalize_amount(self, amount: Any) -> Optional[float]:
        """Normalize monetary amounts"""
        if amount is None:
            return None

        if isinstance(amount, str):
            # Remove currency symbols and commas
            clean = re.sub(r"[$,]", "", amount.strip())
            try:
                return float(clean)
            except ValueError:
                return None
        elif isinstance(amount, (int, float)):
            return float(amount)

        return None

    def normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize dates to ISO format"""
        if not date_str:
            return None

        # Try different date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date().isoformat()
            except ValueError:
                continue

        return None

    def create_comparison_key(self, record: Dict[str, Any], fields: List[str]) -> str:
        """Create a normalized comparison key from multiple fields"""
        key_parts = []

        for field in fields:
            value = record.get(field)
            if value is not None:
                if field in ["address", "property_address"]:
                    normalized = self.normalize_address(str(value))
                elif field in ["name", "owner_name", "borrower_name", "company_name"]:
                    normalized = self.normalize_name(str(value))
                elif field in ["amount", "loan_amount", "sale_amount"]:
                    normalized = str(self.normalize_amount(value))
                else:
                    normalized = self.normalize_text(str(value))

                if normalized:
                    key_parts.append(normalized)

        return "|".join(key_parts)


class SimilarityScorer:
    """Calculates similarity scores between records"""

    def __init__(self):
        self.normalizer = DataNormalizer()

    def calculate_similarity(
        self,
        record1: Dict[str, Any],
        record2: Dict[str, Any],
        fields: List[str],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate overall similarity score between two records"""
        if not weights:
            weights = {field: 1.0 / len(fields) for field in fields}

        total_score = 0.0
        total_weight = 0.0

        for field in fields:
            weight = weights.get(field, 1.0)
            score = self._field_similarity(
                record1.get(field), record2.get(field), field
            )
            total_score += score * weight
            total_weight += weight

        return total_score / max(total_weight, 1.0)

    def _field_similarity(self, value1: Any, value2: Any, field_name: str) -> float:
        """Calculate similarity for a specific field"""
        if value1 is None and value2 is None:
            return 1.0
        if value1 is None or value2 is None:
            return 0.0

        # Convert to strings for comparison
        str1 = str(value1).strip()
        str2 = str(value2).strip()

        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0

        # Field-specific similarity calculations
        if field_name in ["amount", "loan_amount", "sale_amount"]:
            return self._amount_similarity(str1, str2)
        elif field_name in ["date", "filing_date", "recording_date"]:
            return self._date_similarity(str1, str2)
        elif field_name in ["name", "owner_name", "borrower_name", "company_name"]:
            return self._name_similarity(str1, str2)
        elif field_name in ["address", "property_address"]:
            return self._address_similarity(str1, str2)
        else:
            return self._text_similarity(str1, str2)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using multiple methods"""
        # Normalize texts
        norm1 = self.normalizer.normalize_text(text1)
        norm2 = self.normalizer.normalize_text(text2)

        if norm1 == norm2:
            return 1.0

        # Sequence matcher (edit distance)
        seq_score = SequenceMatcher(None, norm1, norm2).ratio()

        # Jaccard similarity on words
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 or words2:
            jaccard = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            jaccard = 1.0

        # Combine scores
        return (seq_score * 0.6) + (jaccard * 0.4)

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate name similarity with phonetic matching"""
        norm1 = self.normalizer.normalize_name(name1)
        norm2 = self.normalizer.normalize_name(name2)

        if norm1 == norm2:
            return 1.0

        # Text similarity
        text_sim = self._text_similarity(norm1, norm2)

        # Phonetic similarity using Soundex
        try:
            import jellyfish

            soundex1 = jellyfish.soundex(norm1)
            soundex2 = jellyfish.soundex(norm2)
            phonetic_sim = 1.0 if soundex1 == soundex2 else 0.3
        except ImportError:
            phonetic_sim = 0.0

        return (text_sim * 0.8) + (phonetic_sim * 0.2)

    def _address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate address similarity"""
        norm1 = self.normalizer.normalize_address(addr1)
        norm2 = self.normalizer.normalize_address(addr2)

        if norm1 == norm2:
            return 1.0

        return self._text_similarity(norm1, norm2)

    def _amount_similarity(self, amt1: str, amt2: str) -> float:
        """Calculate amount similarity"""
        try:
            val1 = self.normalizer.normalize_amount(amt1)
            val2 = self.normalizer.normalize_amount(amt2)

            if val1 is None or val2 is None:
                return 0.0

            if val1 == val2:
                return 1.0

            # Allow small differences (e.g., rounding)
            diff = abs(val1 - val2)
            max_val = max(abs(val1), abs(val2))

            if max_val == 0:
                return 1.0

            # Return high similarity for small percentage differences
            percent_diff = diff / max_val
            return max(0.0, 1.0 - percent_diff)

        except:
            return 0.0

    def _date_similarity(self, date1: str, date2: str) -> float:
        """Calculate date similarity"""
        try:
            norm1 = self.normalizer.normalize_date(date1)
            norm2 = self.normalizer.normalize_date(date2)

            if norm1 == norm2:
                return 1.0

            if norm1 and norm2:
                dt1 = datetime.fromisoformat(norm1)
                dt2 = datetime.fromisoformat(norm2)
                days_diff = abs((dt1 - dt2).days)

                # Allow small date differences
                if days_diff == 0:
                    return 1.0
                elif days_diff <= 7:  # Within a week
                    return 0.8
                elif days_diff <= 30:  # Within a month
                    return 0.6
                else:
                    return 0.3

        except:
            pass

        return 0.0


class DeduplicationEngine:
    """Core deduplication engine with multiple algorithms"""

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.normalizer = DataNormalizer()
        self.similarity_scorer = SimilarityScorer()
        self._lock = threading.Lock()

    def deduplicate_exact_match(
        self, records: List[Dict[str, Any]], key_fields: List[str]
    ) -> List[DuplicateGroup]:
        """Find exact duplicates based on normalized key fields"""
        groups = []
        seen_keys = {}

        for record in records:
            key = self.normalizer.create_comparison_key(record, key_fields)

            if key in seen_keys:
                # Add to existing group
                group = seen_keys[key]
                group.duplicate_records.append(record)
            else:
                # Create new group
                group = DuplicateGroup(
                    group_id=f"exact_{hash(key) % 1000000}",
                    canonical_record=record,
                    confidence_score=1.0,
                    merge_strategy="exact_match",
                )
                seen_keys[key] = group
                groups.append(group)

        # Only return groups with duplicates
        return [g for g in groups if g.duplicate_count > 0]

    def deduplicate_fuzzy_match(
        self, records: List[Dict[str, Any]], fields: List[str], batch_size: int = 1000
    ) -> List[DuplicateGroup]:
        """Find fuzzy duplicates using similarity scoring"""
        groups = []
        processed_records = set()
        record_index = {id(r): r for r in records}

        # Process in batches to manage memory
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            for record in batch:
                if id(record) in processed_records:
                    continue

                # Find similar records
                similar_records = self._find_similar_records(
                    record, batch, fields, processed_records
                )

                if similar_records:
                    # Create group
                    group = DuplicateGroup(
                        group_id=f"fuzzy_{hash(str(id(record))) % 1000000}",
                        canonical_record=record,
                        duplicate_records=similar_records,
                        confidence_score=self.similarity_threshold,
                        merge_strategy="fuzzy_match",
                    )
                    groups.append(group)

                    # Mark all records in group as processed
                    processed_records.add(id(record))
                    for rec in similar_records:
                        processed_records.add(id(rec))

        return groups

    def deduplicate_clustering(
        self,
        records: List[Dict[str, Any]],
        fields: List[str],
        min_cluster_size: int = 2,
    ) -> List[DuplicateGroup]:
        """Use clustering algorithm for deduplication"""
        if len(records) < min_cluster_size:
            return []

        # Create feature vectors from text fields
        texts = []
        for record in records:
            text_parts = []
            for field in fields:
                value = record.get(field)
                if value:
                    text_parts.append(str(value))
            texts.append(" ".join(text_parts))

        if not texts:
            return []

        # TF-IDF vectorization
        try:
            import numpy as np
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ImportError:
            logger.warning("sklearn not available, skipping clustering deduplication")
            return []

        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(tfidf_matrix)

        # Find clusters above threshold
        groups = []
        processed = set()

        for i in range(len(records)):
            if i in processed:
                continue

            cluster_records = []
            cluster_indices = []

            for j in range(len(records)):
                if j in processed:
                    continue

                if similarity_matrix[i][j] >= self.similarity_threshold:
                    cluster_records.append(records[j])
                    cluster_indices.append(j)

            if len(cluster_records) >= min_cluster_size:
                # Create group with highest quality record as canonical
                canonical_idx = self._select_canonical_record(cluster_records)
                canonical = cluster_records[canonical_idx]
                duplicates = [
                    r for idx, r in enumerate(cluster_records) if idx != canonical_idx
                ]

                group = DuplicateGroup(
                    group_id=f"cluster_{hash(str(cluster_indices)) % 1000000}",
                    canonical_record=canonical,
                    duplicate_records=duplicates,
                    confidence_score=self.similarity_threshold,
                    merge_strategy="clustering",
                )
                groups.append(group)

                # Mark as processed
                for idx in cluster_indices:
                    processed.add(idx)

        return groups

    def _find_similar_records(
        self,
        target_record: Dict[str, Any],
        candidate_records: List[Dict[str, Any]],
        fields: List[str],
        processed: Set[int],
    ) -> List[Dict[str, Any]]:
        """Find records similar to target record"""
        similar = []

        for candidate in candidate_records:
            if id(candidate) == id(target_record) or id(candidate) in processed:
                continue

            similarity = self.similarity_scorer.calculate_similarity(
                target_record, candidate, fields
            )

            if similarity >= self.similarity_threshold:
                similar.append(candidate)

        return similar

    def _select_canonical_record(self, records: List[Dict[str, Any]]) -> int:
        """Select the best canonical record from a group"""
        # Score based on data completeness and recency
        best_score = -1
        best_idx = 0

        for idx, record in enumerate(records):
            score = 0

            # Completeness score (number of non-empty fields)
            completeness = sum(
                1 for v in record.values() if v is not None and str(v).strip()
            )
            score += completeness * 10

            # Recency score (prefer newer records)
            date_fields = ["date", "filing_date", "recording_date", "created_at"]
            for field in date_fields:
                date_val = record.get(field)
                if date_val:
                    try:
                        if isinstance(date_val, str):
                            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        elif isinstance(date_val, datetime):
                            dt = date_val
                        else:
                            continue

                        # Score based on how recent the record is
                        days_old = (datetime.utcnow() - dt).days
                        recency_score = max(
                            0, 100 - days_old
                        )  # Prefer records less than 100 days old
                        score += recency_score
                        break
                    except:
                        pass

            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx


class DeduplicationService:
    """High-level service for data deduplication operations"""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.engine = DeduplicationEngine()
        self.metrics = DeduplicationMetrics()

    def deduplicate_records(
        self,
        records: List[Dict[str, Any]],
        algorithm: str = "exact_match",
        fields: Optional[List[str]] = None,
        threshold: float = 0.8,
    ) -> Tuple[List[DuplicateGroup], DeduplicationMetrics]:
        """Main deduplication method"""
        start_time = time.time()
        self.metrics = DeduplicationMetrics(
            algorithm_used=algorithm,
            similarity_threshold=threshold,
            start_time=datetime.utcnow(),
            total_records_processed=len(records),
        )

        # Default fields for different algorithms
        if not fields:
            if algorithm == "exact_match":
                fields = ["name", "address", "amount", "date"]
            else:
                fields = ["name", "address", "amount"]

        self.engine.similarity_threshold = threshold

        # Run deduplication algorithm
        if algorithm == "exact_match":
            groups = self.engine.deduplicate_exact_match(records, fields)
        elif algorithm == "fuzzy_match":
            groups = self.engine.deduplicate_fuzzy_match(records, fields)
        elif algorithm == "clustering":
            groups = self.engine.deduplicate_clustering(records, fields)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Update metrics
        total_duplicates = sum(g.duplicate_count for g in groups)
        self.metrics.duplicates_found = total_duplicates
        self.metrics.duplicate_groups_created = len(groups)
        self.metrics.processing_time_seconds = time.time() - start_time
        self.metrics.end_time = datetime.utcnow()

        logger.info(
            f"Deduplication complete: {len(groups)} groups, {total_duplicates} duplicates found"
        )

        return groups, self.metrics

    def merge_duplicates(
        self, groups: List[DuplicateGroup], merge_strategy: str = "keep_canonical"
    ) -> List[Dict[str, Any]]:
        """Merge duplicate records according to strategy"""
        merged_records = []

        for group in groups:
            if merge_strategy == "keep_canonical":
                # Keep the canonical record, discard duplicates
                merged_records.append(group.canonical_record)
                self.metrics.records_deleted += group.duplicate_count

            elif merge_strategy == "merge_fields":
                # Merge fields from duplicates into canonical
                merged = dict(group.canonical_record)
                for dup in group.duplicate_records:
                    for key, value in dup.items():
                        if key not in merged or merged[key] is None:
                            merged[key] = value
                        # Could add more sophisticated merging logic here
                merged_records.append(merged)
                self.metrics.records_deleted += group.duplicate_count
                self.metrics.records_merged += 1

            elif merge_strategy == "create_compound":
                # Create compound record with all information
                compound = {
                    "canonical_record": group.canonical_record,
                    "duplicate_records": group.duplicate_records,
                    "merged_at": datetime.utcnow().isoformat(),
                    "group_id": group.group_id,
                }
                merged_records.append(compound)
                self.metrics.records_deleted += group.duplicate_count
                self.metrics.records_merged += 1

        self.metrics.records_merged = len(merged_records)
        return merged_records

    def deduplicate_database(
        self,
        jurisdiction_id: int = None,
        record_type: str = None,
        algorithm: str = "exact_match",
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """Deduplicate records in the database"""
        if not self.db_manager:
            raise ValueError("Database manager required for database deduplication")

        # Get records from database
        records = self.db_manager.get_records_for_deduplication(
            jurisdiction_id=jurisdiction_id,
            record_type=record_type,
            limit=batch_size * 10,  # Get more records for better deduplication
        )

        if not records:
            return {"message": "No records found for deduplication"}

        # Run deduplication
        groups, metrics = self.deduplicate_records(records, algorithm)

        # Merge duplicates in database
        merge_results = self._merge_duplicates_in_db(groups)

        return {
            "groups_found": len(groups),
            "duplicates_removed": sum(g.duplicate_count for g in groups),
            "records_remaining": len(records) - sum(g.duplicate_count for g in groups),
            "metrics": metrics.to_dict(),
            "merge_results": merge_results,
        }

    def _merge_duplicates_in_db(self, groups: List[DuplicateGroup]) -> Dict[str, int]:
        """Merge duplicate groups in database"""
        deleted_count = 0
        merged_count = 0

        for group in groups:
            try:
                # Keep canonical record, delete duplicates
                canonical_id = group.canonical_record.get("id")
                duplicate_ids = [
                    r.get("id") for r in group.duplicate_records if r.get("id")
                ]

                if canonical_id and duplicate_ids:
                    # Mark duplicates as deleted or merged
                    for dup_id in duplicate_ids:
                        self.db_manager.mark_record_as_duplicate(dup_id, canonical_id)
                        deleted_count += 1

                merged_count += 1

            except Exception as e:
                logger.error(f"Failed to merge group {group.group_id}: {e}")

        return {"records_deleted": deleted_count, "groups_processed": merged_count}

    def get_deduplication_report(self, groups: List[DuplicateGroup]) -> Dict[str, Any]:
        """Generate detailed deduplication report"""
        report = {
            "summary": {
                "total_groups": len(groups),
                "total_duplicates": sum(g.duplicate_count for g in groups),
                "avg_duplicates_per_group": (
                    sum(g.duplicate_count for g in groups) / max(1, len(groups))
                ),
                "largest_group": max((g.duplicate_count for g in groups), default=0),
            },
            "confidence_distribution": self._analyze_confidence_distribution(groups),
            "field_importance": self._analyze_field_importance(groups),
            "groups": [g.to_dict() for g in groups[:10]],  # First 10 groups as examples
        }

        return report

    def _analyze_confidence_distribution(
        self, groups: List[DuplicateGroup]
    ) -> Dict[str, int]:
        """Analyze confidence score distribution"""
        distribution = defaultdict(int)

        for group in groups:
            score_range = f"{int(group.confidence_score * 10) / 10:.1f}"
            distribution[score_range] += 1

        return dict(sorted(distribution.items()))

    def _analyze_field_importance(
        self, groups: List[DuplicateGroup]
    ) -> Dict[str, float]:
        """Analyze which fields contribute most to matches"""
        # This would require more sophisticated analysis
        # For now, return placeholder
        return {"name": 0.4, "address": 0.3, "amount": 0.2, "date": 0.1}

    def export_deduplication_results(
        self, groups: List[DuplicateGroup], filepath: str, format: str = "json"
    ):
        """Export deduplication results"""
        if format == "json":
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "groups": [g.to_dict() for g in groups],
                "metrics": self.metrics.to_dict(),
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

        elif format == "csv":
            import csv

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["group_id", "confidence", "total_records", "canonical_record_id"]
                )

                for group in groups:
                    canonical_id = group.canonical_record.get("id", "N/A")
                    writer.writerow(
                        [
                            group.group_id,
                            group.confidence_score,
                            group.total_records,
                            canonical_id,
                        ]
                    )

        logger.info(f"Exported deduplication results to {filepath}")
