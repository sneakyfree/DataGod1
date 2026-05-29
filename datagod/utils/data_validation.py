import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataValidator:
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.quality_metrics = {
            "completeness": 0.0,
            "accuracy": 0.0,
            "consistency": 0.0,
            "timeliness": 0.0,
        }

    def _load_validation_rules(self) -> Dict[str, Dict]:
        """Load validation rules from configuration"""
        return {
            "jurisdiction": {
                "required_fields": ["name", "state"],
                "state_pattern": r"^[A-Z]{2}$",
                "name_pattern": r"^[A-Za-z0-9\s\-\.\'\(\)]+$",
            },
            "record": {
                "required_fields": ["source_id", "record_type", "data"],
                "record_type_options": [
                    "person",
                    "property",
                    "business",
                    "court",
                    "legal",
                ],
                "data_format": "json",
            },
        }

    def validate_jurisdiction(
        self, jurisdiction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate jurisdiction data"""
        errors = []
        warnings = []

        # Check required fields
        required_fields = self.validation_rules["jurisdiction"]["required_fields"]
        for field in required_fields:
            if field not in jurisdiction_data or not jurisdiction_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Validate state format
        if "state" in jurisdiction_data:
            state = jurisdiction_data["state"]
            if not re.match(
                self.validation_rules["jurisdiction"]["state_pattern"], state
            ):
                errors.append(f"State '{state}' is not a valid US state abbreviation")

        # Validate name format
        if "name" in jurisdiction_data:
            name = jurisdiction_data["name"]
            if not re.match(
                self.validation_rules["jurisdiction"]["name_pattern"], name
            ):
                warnings.append(f"Name '{name}' contains invalid characters")

        # Check for duplicates (this would be database-level in practice)
        # For now, we'll just log the validation

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate record data"""
        errors = []
        warnings = []

        # Check required fields
        required_fields = self.validation_rules["record"]["required_fields"]
        for field in required_fields:
            if field not in record_data or not record_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Validate record type
        if "record_type" in record_data:
            record_type = record_data["record_type"]
            if (
                record_type
                not in self.validation_rules["record"]["record_type_options"]
            ):
                errors.append(f"Record type '{record_type}' is not valid")

        # Validate data format
        if "data" in record_data:
            if not isinstance(record_data["data"], dict):
                errors.append("Data field must be a JSON object")
            else:
                # Check for potentially problematic data
                data_str = json.dumps(record_data["data"])
                if len(data_str) > 1000000:  # 1MB limit
                    warnings.append("Data field is very large (>1MB)")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def calculate_quality_metrics(
        self, data: Dict[str, Any], source: str
    ) -> Dict[str, float]:
        """Calculate data quality metrics"""
        # This is a simplified implementation
        # In practice, this would be more complex with historical tracking

        completeness = self._calculate_completeness(data)
        accuracy = self._calculate_accuracy(data)
        consistency = self._calculate_consistency(data)
        timeliness = self._calculate_timeliness(data)

        self.quality_metrics = {
            "completeness": completeness,
            "accuracy": accuracy,
            "consistency": consistency,
            "timeliness": timeliness,
        }

        return self.quality_metrics

    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score"""
        if not data:
            return 0.0

        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None and v != "")
        return filled_fields / total_fields if total_fields > 0 else 0.0

    def _calculate_accuracy(self, data: Dict[str, Any]) -> float:
        """Calculate accuracy score"""
        # Placeholder - would implement actual accuracy checks
        return 0.95  # Assume 95% accuracy for now

    def _calculate_consistency(self, data: Dict[str, Any]) -> float:
        """Calculate consistency score"""
        # Placeholder - would implement actual consistency checks
        return 0.90  # Assume 90% consistency for now

    def _calculate_timeliness(self, data: Dict[str, Any]) -> float:
        """Calculate timeliness score"""
        # Placeholder - would implement actual timeliness checks
        return 0.85  # Assume 85% timeliness for now


# Global validator instance
validator = DataValidator()
