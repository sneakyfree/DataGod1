"""
Source Labels / Honest Unknown Labeling (DNA Strand Gene 2.2)

Implements provenance tracking for every data point with
verified/stated/estimated/unknown classification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SourceConfidence(str, Enum):
    """Provenance confidence levels per DNA Strand Law 1."""

    VERIFIED = "verified"  # Confirmed from authoritative source
    STATED = "stated"  # Claimed by party, not independently verified
    ESTIMATED = "estimated"  # Derived from calculation or model
    INFERRED = "inferred"  # Inferred from related data
    UNKNOWN = "unknown"  # Provenance not established


@dataclass
class LabeledValue:
    """
    A data point wrapped with provenance metadata.

    Every value in the system should carry its source label
    for audit-grade traceability.
    """

    value: Any
    label: SourceConfidence
    source: str = ""  # Where the data came from
    source_date: Optional[str] = None  # When it was sourced
    confidence_score: float = 1.0  # 0-1 numeric confidence
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label.value,
            "source": self.source,
            "source_date": self.source_date,
            "confidence_score": round(self.confidence_score, 4),
            "notes": self.notes,
        }

    @property
    def is_trustworthy(self) -> bool:
        """Whether this value has verified or stated provenance."""
        return self.label in (SourceConfidence.VERIFIED, SourceConfidence.STATED)


def label_data(
    value: Any,
    label: SourceConfidence,
    source: str = "",
    confidence: float = 1.0,
) -> LabeledValue:
    """Convenience function to create a LabeledValue."""
    return LabeledValue(
        value=value,
        label=label,
        source=source,
        confidence_score=confidence,
    )


def label_verified(value: Any, source: str = "") -> LabeledValue:
    """Label a value as verified from an authoritative source."""
    return LabeledValue(value=value, label=SourceConfidence.VERIFIED, source=source)


def label_stated(value: Any, source: str = "") -> LabeledValue:
    """Label a value as stated by a party (unverified)."""
    return LabeledValue(
        value=value, label=SourceConfidence.STATED, source=source, confidence_score=0.7
    )


def label_estimated(
    value: Any, source: str = "", confidence: float = 0.5
) -> LabeledValue:
    """Label a value as estimated or derived."""
    return LabeledValue(
        value=value,
        label=SourceConfidence.ESTIMATED,
        source=source,
        confidence_score=confidence,
    )


def label_unknown(value: Any) -> LabeledValue:
    """Label a value with unknown provenance."""
    return LabeledValue(
        value=value, label=SourceConfidence.UNKNOWN, confidence_score=0.0
    )
