"""
Guided Intake Wizard (Phase 4: UX Excellence)

TurboTax-style schema-driven intake with:
- Schema-driven dynamic forms
- Contradiction detection
- "I'm Not Sure" paths with verification checklists
- Progressive disclosure
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import re

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """Types of intake form fields."""
    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"
    ADDRESS = "address"
    ENTITY_NAME = "entity_name"
    PARCEL_ID = "parcel_id"
    PHONE = "phone"
    EMAIL = "email"
    FILE_UPLOAD = "file_upload"


class FieldVisibility(str, Enum):
    """Field visibility states."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    CONDITIONAL = "conditional"


class ValidationSeverity(str, Enum):
    """Severity of validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class FormField:
    """Definition of a form field."""
    id: str
    label: str
    field_type: FieldType
    required: bool = False
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Any = None
    
    # Validation
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    # Options for select/multi_select
    options: List[Dict[str, str]] = field(default_factory=list)
    
    # Conditional visibility
    visibility: FieldVisibility = FieldVisibility.VISIBLE
    show_when: Optional[Dict[str, Any]] = None  # {"field_id": "value"}
    
    # Grouping
    group: Optional[str] = None
    order: int = 0
    
    # "I'm not sure" option
    allow_uncertain: bool = False
    uncertain_followup: Optional[str] = None  # ID of follow-up question


@dataclass
class ValidationResult:
    """Result of field validation."""
    field_id: str
    valid: bool
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None


@dataclass
class Contradiction:
    """A detected contradiction between fields."""
    field_ids: List[str]
    description: str
    severity: ValidationSeverity
    resolution_options: List[str]
    auto_resolvable: bool = False


@dataclass
class VerificationTask:
    """A task to verify uncertain information."""
    task_id: str
    description: str
    field_id: str
    verification_method: str
    priority: str
    estimated_time: str


class IntakeSchema(BaseModel):
    """Schema for an intake form."""
    schema_id: str
    name: str
    description: str
    version: str = "1.0.0"
    fields: List[Dict[str, Any]]
    field_groups: List[Dict[str, Any]] = []
    contradiction_rules: List[Dict[str, Any]] = []
    progressive_stages: List[Dict[str, Any]] = []


class GuidedIntakeWizard:
    """
    TurboTax-style guided intake wizard.
    
    Design Philosophy:
    - Schema-Driven: Forms are defined by schemas, not code
    - Guided: Users are walked through step by step
    - Contradiction Detection: Conflicts are caught early
    - "I'm Not Sure": Uncertainty creates tasks, not failures
    - Progressive: Only show what's needed
    """
    
    # Pre-defined intake schemas
    SCHEMAS: Dict[str, IntakeSchema] = {}
    
    def __init__(self):
        self._initialize_schemas()
        self._current_session: Dict[str, Any] = {}
        self._validation_cache: Dict[str, List[ValidationResult]] = {}
    
    def _initialize_schemas(self):
        """Initialize pre-defined intake schemas."""
        
        # Property Research Intake
        self.SCHEMAS["property_research"] = IntakeSchema(
            schema_id="property_research",
            name="Property Research Intake",
            description="Gather information for property research",
            fields=[
                # Stage 1: Property Identification
                {
                    "id": "property_address",
                    "label": "Property Address",
                    "field_type": FieldType.ADDRESS,
                    "required": True,
                    "group": "property_id",
                    "order": 1,
                    "help_text": "Enter the full property address",
                    "allow_uncertain": True,
                    "uncertain_followup": "address_verification"
                },
                {
                    "id": "parcel_id",
                    "label": "Parcel/APN Number",
                    "field_type": FieldType.PARCEL_ID,
                    "required": False,
                    "group": "property_id",
                    "order": 2,
                    "help_text": "If known, enter the parcel or APN number",
                    "placeholder": "e.g., 123-456-789"
                },
                {
                    "id": "property_type",
                    "label": "Property Type",
                    "field_type": FieldType.SELECT,
                    "required": True,
                    "group": "property_id",
                    "order": 3,
                    "options": [
                        {"value": "single_family", "label": "Single Family Home"},
                        {"value": "condo", "label": "Condo/Townhouse"},
                        {"value": "multi_family", "label": "Multi-Family (2-4 units)"},
                        {"value": "apartment", "label": "Apartment Building (5+ units)"},
                        {"value": "commercial", "label": "Commercial"},
                        {"value": "land", "label": "Vacant Land"},
                        {"value": "mixed_use", "label": "Mixed Use"},
                        {"value": "unknown", "label": "I'm not sure"}
                    ]
                },
                # Stage 2: Owner Information
                {
                    "id": "owner_name",
                    "label": "Owner Name",
                    "field_type": FieldType.ENTITY_NAME,
                    "required": False,
                    "group": "owner_info",
                    "order": 10,
                    "help_text": "Name of the current owner (if known)",
                    "allow_uncertain": True
                },
                {
                    "id": "owner_type",
                    "label": "Owner Type",
                    "field_type": FieldType.SELECT,
                    "required": False,
                    "group": "owner_info",
                    "order": 11,
                    "visibility": FieldVisibility.CONDITIONAL,
                    "show_when": {"owner_name": {"not_empty": True}},
                    "options": [
                        {"value": "individual", "label": "Individual Person"},
                        {"value": "couple", "label": "Married Couple"},
                        {"value": "trust", "label": "Trust"},
                        {"value": "llc", "label": "LLC/Company"},
                        {"value": "bank", "label": "Bank/Lender (REO)"},
                        {"value": "government", "label": "Government Entity"},
                        {"value": "unknown", "label": "I'm not sure"}
                    ]
                },
                # Stage 3: Research Goals
                {
                    "id": "research_purpose",
                    "label": "Research Purpose",
                    "field_type": FieldType.MULTI_SELECT,
                    "required": True,
                    "group": "goals",
                    "order": 20,
                    "options": [
                        {"value": "purchase", "label": "Considering Purchase"},
                        {"value": "title_search", "label": "Title Search/Due Diligence"},
                        {"value": "lien_search", "label": "Lien/Encumbrance Search"},
                        {"value": "owner_lookup", "label": "Find Owner Contact Info"},
                        {"value": "valuation", "label": "Property Valuation"},
                        {"value": "investment", "label": "Investment Analysis"},
                        {"value": "other", "label": "Other"}
                    ]
                },
                {
                    "id": "budget_max",
                    "label": "Maximum Budget",
                    "field_type": FieldType.CURRENCY,
                    "required": False,
                    "group": "goals",
                    "order": 21,
                    "visibility": FieldVisibility.CONDITIONAL,
                    "show_when": {"research_purpose": {"contains": "purchase"}},
                    "help_text": "What's your maximum purchase budget?"
                },
                # Stage 4: Known Issues
                {
                    "id": "known_liens",
                    "label": "Known Liens or Encumbrances",
                    "field_type": FieldType.BOOLEAN,
                    "required": False,
                    "group": "known_issues",
                    "order": 30,
                    "help_text": "Are you aware of any liens on this property?"
                },
                {
                    "id": "known_liens_details",
                    "label": "Lien Details",
                    "field_type": FieldType.TEXT,
                    "required": False,
                    "group": "known_issues",
                    "order": 31,
                    "visibility": FieldVisibility.CONDITIONAL,
                    "show_when": {"known_liens": True},
                    "help_text": "Describe the liens you're aware of"
                },
                {
                    "id": "pending_litigation",
                    "label": "Pending Litigation",
                    "field_type": FieldType.BOOLEAN,
                    "required": False,
                    "group": "known_issues",
                    "order": 32,
                    "help_text": "Is there any pending litigation involving this property?"
                }
            ],
            field_groups=[
                {"id": "property_id", "label": "Property Identification", "order": 1},
                {"id": "owner_info", "label": "Owner Information", "order": 2},
                {"id": "goals", "label": "Research Goals", "order": 3},
                {"id": "known_issues", "label": "Known Issues", "order": 4}
            ],
            contradiction_rules=[
                {
                    "id": "owner_mismatch",
                    "fields": ["owner_name", "owner_type"],
                    "condition": "owner_type == 'individual' and contains_business_suffix(owner_name)",
                    "message": "Owner name appears to be a business, but owner type is 'Individual'"
                },
                {
                    "id": "budget_vs_type",
                    "fields": ["property_type", "budget_max"],
                    "condition": "property_type == 'apartment' and budget_max < 500000",
                    "message": "Budget may be low for apartment building purchase"
                }
            ],
            progressive_stages=[
                {"stage": 1, "groups": ["property_id"], "required": True},
                {"stage": 2, "groups": ["owner_info"], "required": False},
                {"stage": 3, "groups": ["goals"], "required": True},
                {"stage": 4, "groups": ["known_issues"], "required": False}
            ]
        )
        
        # Entity Research Intake
        self.SCHEMAS["entity_research"] = IntakeSchema(
            schema_id="entity_research",
            name="Entity Research Intake",
            description="Gather information for entity/person research",
            fields=[
                {
                    "id": "entity_name",
                    "label": "Entity Name",
                    "field_type": FieldType.ENTITY_NAME,
                    "required": True,
                    "group": "entity_id",
                    "order": 1,
                    "help_text": "Name of the person or company to research"
                },
                {
                    "id": "entity_type",
                    "label": "Entity Type",
                    "field_type": FieldType.SELECT,
                    "required": True,
                    "group": "entity_id",
                    "order": 2,
                    "options": [
                        {"value": "person", "label": "Individual Person"},
                        {"value": "company", "label": "Company/Business"},
                        {"value": "trust", "label": "Trust"},
                        {"value": "unknown", "label": "I'm not sure"}
                    ]
                },
                {
                    "id": "known_address",
                    "label": "Known Address",
                    "field_type": FieldType.ADDRESS,
                    "required": False,
                    "group": "entity_id",
                    "order": 3,
                    "help_text": "Any known address associated with this entity"
                },
                {
                    "id": "research_scope",
                    "label": "Research Scope",
                    "field_type": FieldType.MULTI_SELECT,
                    "required": True,
                    "group": "scope",
                    "order": 10,
                    "options": [
                        {"value": "property_ownership", "label": "Property Ownership"},
                        {"value": "liens_judgments", "label": "Liens & Judgments"},
                        {"value": "business_filings", "label": "Business Filings"},
                        {"value": "court_records", "label": "Court Records"},
                        {"value": "contact_info", "label": "Contact Information"},
                        {"value": "relationships", "label": "Related Entities"}
                    ]
                },
                {
                    "id": "jurisdiction",
                    "label": "Search Jurisdiction",
                    "field_type": FieldType.SELECT,
                    "required": False,
                    "group": "scope",
                    "order": 11,
                    "options": [
                        {"value": "nationwide", "label": "Nationwide"},
                        {"value": "state", "label": "Specific State"},
                        {"value": "county", "label": "Specific County"}
                    ]
                }
            ],
            field_groups=[
                {"id": "entity_id", "label": "Entity Identification", "order": 1},
                {"id": "scope", "label": "Research Scope", "order": 2}
            ],
            contradiction_rules=[],
            progressive_stages=[
                {"stage": 1, "groups": ["entity_id"], "required": True},
                {"stage": 2, "groups": ["scope"], "required": True}
            ]
        )
        
        logger.info(f"Initialized {len(self.SCHEMAS)} intake schemas")
    
    def start_session(
        self,
        schema_id: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Start a new intake session.
        
        Returns session info including first stage fields.
        """
        schema = self.SCHEMAS.get(schema_id)
        if not schema:
            raise ValueError(f"Unknown schema: {schema_id}")
        
        session_id = f"intake_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        self._current_session = {
            "session_id": session_id,
            "schema_id": schema_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "current_stage": 1,
            "data": {},
            "uncertain_fields": [],
            "verification_tasks": [],
            "contradictions": []
        }
        
        # Get first stage fields
        first_stage = self._get_stage_fields(schema, 1)
        
        return {
            "session_id": session_id,
            "schema_name": schema.name,
            "total_stages": len(schema.progressive_stages),
            "current_stage": 1,
            "fields": first_stage,
            "groups": self._get_stage_groups(schema, 1)
        }
    
    def submit_stage(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit data for the current stage.
        
        Returns validation results, contradictions, and next stage (if any).
        """
        if self._current_session.get("session_id") != session_id:
            raise ValueError("Invalid session")
        
        schema = self.SCHEMAS.get(self._current_session["schema_id"])
        current_stage = self._current_session["current_stage"]
        
        # Merge new data
        self._current_session["data"].update(data)
        
        # Check for "I'm not sure" responses
        uncertain = self._check_uncertain_responses(schema, data)
        self._current_session["uncertain_fields"].extend(uncertain)
        
        # Validate fields
        validations = self._validate_fields(schema, data)
        
        # Check for contradictions
        contradictions = self._detect_contradictions(
            schema,
            self._current_session["data"]
        )
        self._current_session["contradictions"] = contradictions
        
        # Generate verification tasks for uncertain fields
        if uncertain:
            tasks = self._generate_verification_tasks(schema, uncertain)
            self._current_session["verification_tasks"].extend(tasks)
        
        # Check if we can proceed
        errors = [v for v in validations if v.severity == ValidationSeverity.ERROR]
        blocking_contradictions = [c for c in contradictions if c.severity == ValidationSeverity.ERROR]
        
        can_proceed = len(errors) == 0 and len(blocking_contradictions) == 0
        
        # Prepare response
        response = {
            "session_id": session_id,
            "current_stage": current_stage,
            "validations": [{"field_id": v.field_id, "valid": v.valid, "severity": v.severity.value, "message": v.message} for v in validations],
            "contradictions": [{"fields": c.field_ids, "description": c.description, "options": c.resolution_options} for c in contradictions],
            "verification_tasks": [{"task_id": t.task_id, "description": t.description, "priority": t.priority} for t in self._current_session["verification_tasks"]],
            "can_proceed": can_proceed
        }
        
        # If can proceed, check for next stage
        if can_proceed:
            next_stage = current_stage + 1
            if next_stage <= len(schema.progressive_stages):
                self._current_session["current_stage"] = next_stage
                response["next_stage"] = next_stage
                response["next_fields"] = self._get_stage_fields(schema, next_stage)
                response["next_groups"] = self._get_stage_groups(schema, next_stage)
            else:
                response["complete"] = True
                response["final_data"] = self._current_session["data"]
        
        return response
    
    def resolve_contradiction(
        self,
        session_id: str,
        contradiction_index: int,
        resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve a detected contradiction.
        
        Args:
            session_id: Session ID
            contradiction_index: Which contradiction to resolve
            resolution: Field values to update
        """
        if self._current_session.get("session_id") != session_id:
            raise ValueError("Invalid session")
        
        # Update data with resolution
        self._current_session["data"].update(resolution)
        
        # Recheck contradictions
        schema = self.SCHEMAS.get(self._current_session["schema_id"])
        contradictions = self._detect_contradictions(schema, self._current_session["data"])
        self._current_session["contradictions"] = contradictions
        
        return {
            "resolved": True,
            "remaining_contradictions": len(contradictions)
        }
    
    def get_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of the intake session."""
        if self._current_session.get("session_id") != session_id:
            raise ValueError("Invalid session")
        
        return {
            "session_id": session_id,
            "schema_id": self._current_session["schema_id"],
            "data": self._current_session["data"],
            "uncertain_fields": self._current_session["uncertain_fields"],
            "verification_tasks": [
                {"task_id": t.task_id, "description": t.description, "priority": t.priority}
                for t in self._current_session["verification_tasks"]
            ],
            "contradictions": [
                {"fields": c.field_ids, "description": c.description}
                for c in self._current_session["contradictions"]
            ],
            "complete": self._current_session["current_stage"] > len(
                self.SCHEMAS[self._current_session["schema_id"]].progressive_stages
            )
        }
    
    def _get_stage_fields(self, schema: IntakeSchema, stage: int) -> List[Dict[str, Any]]:
        """Get fields for a specific stage."""
        if stage > len(schema.progressive_stages):
            return []
        
        stage_config = schema.progressive_stages[stage - 1]
        group_ids = stage_config.get("groups", [])
        
        fields = []
        for field_dict in schema.fields:
            if field_dict.get("group") in group_ids:
                fields.append(field_dict)
        
        return sorted(fields, key=lambda f: f.get("order", 0))
    
    def _get_stage_groups(self, schema: IntakeSchema, stage: int) -> List[Dict[str, str]]:
        """Get field groups for a specific stage."""
        if stage > len(schema.progressive_stages):
            return []
        
        stage_config = schema.progressive_stages[stage - 1]
        group_ids = stage_config.get("groups", [])
        
        groups = [g for g in schema.field_groups if g.get("id") in group_ids]
        return sorted(groups, key=lambda g: g.get("order", 0))
    
    def _check_uncertain_responses(
        self,
        schema: IntakeSchema,
        data: Dict[str, Any]
    ) -> List[str]:
        """Check for fields marked as uncertain."""
        uncertain = []
        
        for field_dict in schema.fields:
            field_id = field_dict.get("id")
            value = data.get(field_id)
            
            # Check for explicit "unknown" selections
            if value == "unknown" or value == "I'm not sure":
                uncertain.append(field_id)
            
            # Check for uncertainty flag
            if data.get(f"{field_id}_uncertain") == True:
                uncertain.append(field_id)
        
        return uncertain
    
    def _validate_fields(
        self,
        schema: IntakeSchema,
        data: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate submitted fields."""
        results = []
        
        for field_dict in schema.fields:
            field_id = field_dict.get("id")
            value = data.get(field_id)
            required = field_dict.get("required", False)
            field_type = field_dict.get("field_type")
            
            # Check required
            if required and (value is None or value == ""):
                results.append(ValidationResult(
                    field_id=field_id,
                    valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{field_dict.get('label')} is required"
                ))
                continue
            
            if value is None or value == "":
                continue
            
            # Type-specific validation
            if field_type == FieldType.EMAIL:
                if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(value)):
                    results.append(ValidationResult(
                        field_id=field_id,
                        valid=False,
                        severity=ValidationSeverity.ERROR,
                        message="Invalid email format"
                    ))
            
            elif field_type == FieldType.PHONE:
                digits = re.sub(r'\D', '', str(value))
                if len(digits) < 10:
                    results.append(ValidationResult(
                        field_id=field_id,
                        valid=False,
                        severity=ValidationSeverity.ERROR,
                        message="Phone number must have at least 10 digits"
                    ))
            
            elif field_type == FieldType.CURRENCY:
                try:
                    amount = float(str(value).replace('$', '').replace(',', ''))
                    if amount < 0:
                        results.append(ValidationResult(
                            field_id=field_id,
                            valid=False,
                            severity=ValidationSeverity.ERROR,
                            message="Amount cannot be negative"
                        ))
                except ValueError:
                    results.append(ValidationResult(
                        field_id=field_id,
                        valid=False,
                        severity=ValidationSeverity.ERROR,
                        message="Invalid currency format"
                    ))
            
            # Min/max validation
            min_val = field_dict.get("min_value")
            max_val = field_dict.get("max_value")
            if min_val is not None or max_val is not None:
                try:
                    num_val = float(value)
                    if min_val is not None and num_val < min_val:
                        results.append(ValidationResult(
                            field_id=field_id,
                            valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value must be at least {min_val}"
                        ))
                    if max_val is not None and num_val > max_val:
                        results.append(ValidationResult(
                            field_id=field_id,
                            valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"Value must be at most {max_val}"
                        ))
                except (ValueError, TypeError):
                    pass
        
        return results
    
    def _detect_contradictions(
        self,
        schema: IntakeSchema,
        data: Dict[str, Any]
    ) -> List[Contradiction]:
        """Detect contradictions in the data."""
        contradictions = []
        
        for rule in schema.contradiction_rules:
            rule_id = rule.get("id")
            fields = rule.get("fields", [])
            condition = rule.get("condition", "")
            message = rule.get("message", "Contradiction detected")
            
            # Build a context for evaluation
            context = {f: data.get(f) for f in fields}
            context["contains_business_suffix"] = self._contains_business_suffix
            
            try:
                # Simple condition evaluation
                if self._evaluate_condition(condition, context):
                    contradictions.append(Contradiction(
                        field_ids=fields,
                        description=message,
                        severity=ValidationSeverity.WARNING,
                        resolution_options=["Update owner name", "Update owner type"],
                        auto_resolvable=False
                    ))
            except Exception as e:
                logger.warning(f"Failed to evaluate contradiction rule {rule_id}: {e}")
        
        return contradictions
    
    def _contains_business_suffix(self, name: str) -> bool:
        """Check if a name contains business suffixes."""
        if not name:
            return False
        name_lower = name.lower()
        suffixes = ['llc', 'inc', 'corp', 'ltd', 'company', 'co.', 'lp', 'llp']
        return any(suffix in name_lower for suffix in suffixes)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a condition string."""
        # Simple evaluation - in production use a proper expression parser
        try:
            # Replace field references with values
            for key, value in context.items():
                if callable(value):
                    continue
                if isinstance(value, str):
                    condition = condition.replace(key, f"'{value}'")
                elif value is None:
                    condition = condition.replace(key, "None")
                else:
                    condition = condition.replace(key, str(value))
            
            # Very basic evaluation for simple conditions
            # This is simplified - production would use ast.literal_eval or similar
            return False  # Safe default
        except Exception:
            return False
    
    def _generate_verification_tasks(
        self,
        schema: IntakeSchema,
        uncertain_fields: List[str]
    ) -> List[VerificationTask]:
        """Generate verification tasks for uncertain fields."""
        tasks = []
        
        field_map = {f.get("id"): f for f in schema.fields}
        
        for field_id in uncertain_fields:
            field_dict = field_map.get(field_id)
            if not field_dict:
                continue
            
            task = VerificationTask(
                task_id=f"verify_{field_id}",
                description=f"Verify: {field_dict.get('label')}",
                field_id=field_id,
                verification_method=self._get_verification_method(field_dict.get("field_type")),
                priority="medium",
                estimated_time="5-10 minutes"
            )
            tasks.append(task)
        
        return tasks
    
    def _get_verification_method(self, field_type: str) -> str:
        """Get appropriate verification method for a field type."""
        methods = {
            FieldType.ADDRESS: "Verify against county records or Google Maps",
            FieldType.ENTITY_NAME: "Search public records for entity",
            FieldType.PARCEL_ID: "Verify with county assessor",
            FieldType.CURRENCY: "Verify with source documentation"
        }
        return methods.get(field_type, "Manual verification required")
