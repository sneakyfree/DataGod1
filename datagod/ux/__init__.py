"""
DataGod UX Package (Phase 4)

Provides UX excellence components:
- Guided Intake Wizard (TurboTax-style)
- Multi-View Report Generator
"""

from .intake_wizard import (
    Contradiction,
    FieldType,
    FieldVisibility,
    FormField,
    GuidedIntakeWizard,
    IntakeSchema,
    ValidationResult,
    VerificationTask,
)
from .report_generator import (
    ExportFormat,
    MultiViewReportGenerator,
    ReportMetadata,
    ReportSection,
    ReportView,
)

__all__ = [
    # Intake Wizard
    "GuidedIntakeWizard",
    "IntakeSchema",
    "FieldType",
    "FieldVisibility",
    "FormField",
    "ValidationResult",
    "Contradiction",
    "VerificationTask",
    # Report Generator
    "MultiViewReportGenerator",
    "ReportView",
    "ExportFormat",
    "ReportSection",
    "ReportMetadata",
]
