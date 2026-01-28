"""
DataGod UX Package (Phase 4)

Provides UX excellence components:
- Guided Intake Wizard (TurboTax-style)
- Multi-View Report Generator
"""

from .intake_wizard import (
    GuidedIntakeWizard,
    IntakeSchema,
    FieldType,
    FieldVisibility,
    FormField,
    ValidationResult,
    Contradiction,
    VerificationTask
)

from .report_generator import (
    MultiViewReportGenerator,
    ReportView,
    ExportFormat,
    ReportSection,
    ReportMetadata
)

__all__ = [
    # Intake Wizard
    'GuidedIntakeWizard',
    'IntakeSchema',
    'FieldType',
    'FieldVisibility',
    'FormField',
    'ValidationResult',
    'Contradiction',
    'VerificationTask',
    # Report Generator
    'MultiViewReportGenerator',
    'ReportView',
    'ExportFormat',
    'ReportSection',
    'ReportMetadata',
]
