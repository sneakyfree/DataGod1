"""
Tests for Reason Code Engine (Gap P2 – FCRA/ECOA Compliance)
"""

import pytest
from datagod.compliance.reason_codes import (
    ReasonCodeEngine,
    ReasonCode,
    ReasonCodeResult,
    ReasonCodeStandard,
    ReasonCodeSeverity,
)


class TestReasonCodeStandard:
    """Test reason code standard enum."""

    def test_standards_exist(self):
        assert ReasonCodeStandard.FCRA == "fcra"
        assert ReasonCodeStandard.ECOA == "ecoa"
        assert ReasonCodeStandard.DATAGOD == "datagod"


class TestReasonCodeSeverity:
    """Test severity enum."""

    def test_severities_exist(self):
        assert ReasonCodeSeverity.CRITICAL == "critical"
        assert ReasonCodeSeverity.HIGH == "high"
        assert ReasonCodeSeverity.MEDIUM == "medium"
        assert ReasonCodeSeverity.LOW == "low"


class TestReasonCodeEngine:
    """Test the core engine."""

    def setup_method(self):
        self.engine = ReasonCodeEngine()

    def test_engine_initializes(self):
        assert self.engine is not None

    def test_list_codes_returns_list(self):
        codes = self.engine.list_codes()
        assert isinstance(codes, list)
        assert len(codes) > 0

    def test_codes_have_required_fields(self):
        codes = self.engine.list_codes()
        for code in codes:
            assert hasattr(code, 'code')
            assert hasattr(code, 'standard')
            assert hasattr(code, 'severity')
            assert hasattr(code, 'description')

    def test_list_codes_by_standard(self):
        fcra = self.engine.list_codes(standard=ReasonCodeStandard.FCRA)
        assert all(c.standard == ReasonCodeStandard.FCRA for c in fcra)
        ecoa = self.engine.list_codes(standard=ReasonCodeStandard.ECOA)
        assert all(c.standard == ReasonCodeStandard.ECOA for c in ecoa)

    def test_generate_codes_for_blockers(self):
        blockers = [
            {"blocker_id": "tax_lien_1", "category": "lien", "description": "Outstanding tax lien"},
            {"blocker_id": "title_defect_1", "category": "title", "description": "Title defect found"},
        ]
        result = self.engine.generate_codes(blockers)
        assert isinstance(result, ReasonCodeResult)

    def test_generate_codes_empty_blockers(self):
        result = self.engine.generate_codes([])
        assert isinstance(result, ReasonCodeResult)
        assert len(result.codes) == 0

    def test_result_to_dict(self):
        result = self.engine.generate_codes([
            {"blocker_id": "test", "category": "compliance", "description": "test blocker"}
        ])
        d = result.to_dict()
        assert "codes" in d
        assert "total_codes" in d

    def test_get_code_by_id(self):
        codes = self.engine.list_codes()
        if codes:
            found = self.engine.get_code(codes[0].code)
            assert found is not None
            assert found.code == codes[0].code

    def test_get_code_not_found(self):
        result = self.engine.get_code("NONEXISTENT_CODE")
        assert result is None

    def test_code_to_dict(self):
        codes = self.engine.list_codes()
        if codes:
            d = codes[0].to_dict()
            assert "code" in d
            assert "standard" in d
            assert "description" in d
