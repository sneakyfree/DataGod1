"""
DataGod Compliance Package (DNA Strand Chromosome 2)

Provides compliance-grade infrastructure:
- Reason Code Engine (FCRA/ECOA/DataGod adverse action codes)
- Fairness Monitoring (disparate impact, jurisdiction bias)
- Source Labels (verified/stated/estimated provenance)
"""

from .fairness import (
    FairnessCheck,
    FairnessMetric,
    FairnessMonitor,
    FairnessReport,
    FairnessStatus,
)
from .reason_codes import (
    ReasonCode,
    ReasonCodeEngine,
    ReasonCodeResult,
    ReasonCodeSeverity,
    ReasonCodeStandard,
)
from .source_labels import (
    LabeledValue,
    SourceConfidence,
    label_data,
    label_estimated,
    label_stated,
    label_unknown,
    label_verified,
)

__all__ = [
    # Reason Codes
    "ReasonCodeEngine",
    "ReasonCode",
    "ReasonCodeResult",
    "ReasonCodeStandard",
    "ReasonCodeSeverity",
    # Fairness
    "FairnessMonitor",
    "FairnessReport",
    "FairnessCheck",
    "FairnessMetric",
    "FairnessStatus",
    # Source Labels
    "SourceConfidence",
    "LabeledValue",
    "label_data",
    "label_verified",
    "label_stated",
    "label_estimated",
    "label_unknown",
]
