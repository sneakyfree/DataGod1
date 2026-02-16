"""
DataGod Compliance Package (DNA Strand Chromosome 2)

Provides compliance-grade infrastructure:
- Reason Code Engine (FCRA/ECOA/DataGod adverse action codes)
- Fairness Monitoring (disparate impact, jurisdiction bias)
- Source Labels (verified/stated/estimated provenance)
"""

from .reason_codes import (
    ReasonCodeEngine,
    ReasonCode,
    ReasonCodeResult,
    ReasonCodeStandard,
    ReasonCodeSeverity,
)

from .fairness import (
    FairnessMonitor,
    FairnessReport,
    FairnessCheck,
    FairnessMetric,
    FairnessStatus,
)

from .source_labels import (
    SourceConfidence,
    LabeledValue,
    label_data,
    label_verified,
    label_stated,
    label_estimated,
    label_unknown,
)

__all__ = [
    # Reason Codes
    'ReasonCodeEngine', 'ReasonCode', 'ReasonCodeResult',
    'ReasonCodeStandard', 'ReasonCodeSeverity',
    # Fairness
    'FairnessMonitor', 'FairnessReport', 'FairnessCheck',
    'FairnessMetric', 'FairnessStatus',
    # Source Labels
    'SourceConfidence', 'LabeledValue',
    'label_data', 'label_verified', 'label_stated',
    'label_estimated', 'label_unknown',
]
