"""
Tests for UX modules — coverage for ux/intake_wizard.py and ux/report_generator.py (0% → 50%+)
"""

import pytest
from datetime import datetime

from datagod.ux.intake_wizard import (
    FieldType,
    FieldVisibility,
    ValidationSeverity,
    FormField,
    ValidationResult,
    Contradiction,
    VerificationTask,
    IntakeSchema,
    GuidedIntakeWizard,
)

from datagod.ux.report_generator import (
    ReportView,
    ExportFormat,
    ReportSection,
    ReportMetadata,
    MultiViewReportGenerator,
)


# ============================================================
# Intake Wizard Tests
# ============================================================

class TestFieldType:
    def test_values(self):
        assert FieldType.TEXT.value == "text"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.CURRENCY.value == "currency"
        assert FieldType.DATE.value == "date"
        assert FieldType.SELECT.value == "select"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.ADDRESS.value == "address"
        assert FieldType.EMAIL.value == "email"


class TestFieldVisibility:
    def test_values(self):
        assert FieldVisibility.VISIBLE.value == "visible"
        assert FieldVisibility.HIDDEN.value == "hidden"
        assert FieldVisibility.CONDITIONAL.value == "conditional"


class TestFormField:
    def test_create(self):
        field = FormField(id="name", label="Full Name", field_type=FieldType.TEXT, required=True)
        assert field.id == "name"
        assert field.label == "Full Name"
        assert field.required is True


class TestIntakeSchema:
    def test_create(self):
        schema = IntakeSchema(
            schema_id="test",
            name="Test Schema",
            description="A test schema",
            fields=[],
        )
        assert schema.schema_id == "test"
        assert schema.name == "Test Schema"


class TestGuidedIntakeWizard:
    def setup_method(self):
        self.wizard = GuidedIntakeWizard()

    def test_wizard_initializes(self):
        assert self.wizard is not None

    def test_schemas_initialized(self):
        assert "property_research" in self.wizard.SCHEMAS
        assert "entity_research" in self.wizard.SCHEMAS

    def test_start_session_property_research(self):
        session = self.wizard.start_session("property_research")
        assert isinstance(session, dict)
        assert "session_id" in session

    def test_start_session_entity_research(self):
        session = self.wizard.start_session("entity_research")
        assert isinstance(session, dict)
        assert "session_id" in session

    def test_start_session_invalid_schema(self):
        with pytest.raises(ValueError):
            self.wizard.start_session("nonexistent_schema")

    def test_submit_stage_property(self):
        session = self.wizard.start_session("property_research")
        sid = session["session_id"]
        result = self.wizard.submit_stage(sid, {
            "property_address": "123 Main St",
            "property_type": "single_family",
        })
        assert isinstance(result, dict)

    def test_submit_stage_empty_data(self):
        session = self.wizard.start_session("property_research")
        sid = session["session_id"]
        result = self.wizard.submit_stage(sid, {})
        assert isinstance(result, dict)

    def test_get_summary(self):
        session = self.wizard.start_session("property_research")
        sid = session["session_id"]
        self.wizard.submit_stage(sid, {"property_address": "123 Main St", "property_type": "condo"})
        summary = self.wizard.get_summary(sid)
        assert isinstance(summary, dict)

    def test_validate_fields(self):
        schema = self.wizard.SCHEMAS.get("property_research")
        results = self.wizard._validate_fields(schema, {"property_address": "123 Main St"})
        assert isinstance(results, list)

    def test_detect_contradictions(self):
        schema = self.wizard.SCHEMAS.get("property_research")
        contradictions = self.wizard._detect_contradictions(schema, {
            "property_address": "123 Main St",
            "owner_name": "John",
        })
        assert isinstance(contradictions, list)

    def test_check_uncertain_responses(self):
        schema = self.wizard.SCHEMAS.get("property_research")
        uncertain = self.wizard._check_uncertain_responses(schema, {
            "property_type": "unknown",
        })
        assert isinstance(uncertain, list)
        assert "property_type" in uncertain

    def test_get_stage_fields(self):
        schema = self.wizard.SCHEMAS.get("property_research")
        fields = self.wizard._get_stage_fields(schema, 1)
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_get_stage_groups(self):
        schema = self.wizard.SCHEMAS.get("property_research")
        groups = self.wizard._get_stage_groups(schema, 1)
        assert isinstance(groups, list)

    def test_resolve_contradiction(self):
        session = self.wizard.start_session("property_research")
        sid = session["session_id"]
        self.wizard.submit_stage(sid, {"property_address": "123 Main"})
        result = self.wizard.resolve_contradiction(sid, 0, {"property_type": "commercial"})
        assert result["resolved"] is True

    def test_contains_business_suffix(self):
        assert self.wizard._contains_business_suffix("Acme LLC") is True
        assert self.wizard._contains_business_suffix("John Smith") is False


# ============================================================
# Report Generator Tests
# ============================================================

class TestReportView:
    def test_values(self):
        assert ReportView.CONSUMER.value == "consumer"
        assert ReportView.OPERATOR.value == "operator"
        assert ReportView.ANALYST.value == "analyst"
        assert ReportView.AUDIT.value == "audit"


class TestExportFormat:
    def test_values(self):
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.MARKDOWN.value == "markdown"


class TestReportSection:
    def test_create(self):
        section = ReportSection(id="summary", title="Summary", content={"text": "Test"})
        assert section.id == "summary"
        assert section.title == "Summary"


class TestMultiViewReportGenerator:
    def setup_method(self):
        self.generator = MultiViewReportGenerator()

    def test_initializes(self):
        assert self.generator is not None

    def test_generate_consumer_report(self):
        data = {
            "property": {"address": "123 Main St", "city": "New York", "state": "NY"},
            "liens": [],
            "scenarios": [],
            "blockers": [],
        }
        report = self.generator.generate(data, view=ReportView.CONSUMER, title="Test Report")
        assert isinstance(report, dict)

    def test_generate_operator_report(self):
        data = {
            "property": {"address": "456 Oak Ave"},
            "liens": [{"type": "mortgage", "amount": 200000}],
        }
        report = self.generator.generate(data, view=ReportView.OPERATOR)
        assert isinstance(report, dict)

    def test_generate_analyst_report(self):
        data = {"property": {"parcel_id": "APN-123"}}
        report = self.generator.generate(data, view=ReportView.ANALYST)
        assert isinstance(report, dict)

    def test_generate_audit_report(self):
        data = {"property": {"parcel_id": "APN-123"}}
        report = self.generator.generate(data, view=ReportView.AUDIT)
        assert isinstance(report, dict)

    def test_generate_all_views(self):
        data = {"property": {"address": "789 Elm St"}}
        all_views = self.generator.generate_all_views(data, title="Multi View")
        assert isinstance(all_views, dict)
        assert len(all_views) >= 4

    def test_export_json(self):
        data = {"property": {"address": "123 Main St"}}
        report = self.generator.generate(data)
        exported = self.generator.export(report, format=ExportFormat.JSON)
        assert isinstance(exported, str)

    def test_export_html(self):
        data = {"property": {"address": "123 Main St"}}
        report = self.generator.generate(data)
        exported = self.generator.export(report, format=ExportFormat.HTML)
        assert isinstance(exported, str)

    def test_export_markdown(self):
        data = {"property": {"address": "123 Main St"}}
        report = self.generator.generate(data)
        exported = self.generator.export(report, format=ExportFormat.MARKDOWN)
        assert isinstance(exported, str)

    def test_generate_footer(self):
        footer = self.generator._generate_footer(ReportView.CONSUMER)
        assert isinstance(footer, dict)

    def test_build_audit_metadata(self):
        metadata = self.generator._build_audit_metadata(
            {"property": {"address": "test"}},
            {"extra": "data"}
        )
        assert isinstance(metadata, dict)

    def test_consumer_property_description(self):
        desc = self.generator._consumer_property_description({
            "address": "123 Main St",
            "city": "New York",
        })
        assert isinstance(desc, str)
