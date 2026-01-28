from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, validator

# --- Enums ---
class RecordType(str, Enum):
    MORTGAGE = "mortgage"
    PROPERTY = "property"
    TAX = "tax"
    LEGAL = "legal"
    FINANCIAL = "financial"

class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PROPERTY = "property"
    GOVERNMENT = "government"

class CoverageStatus(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    UNAVAILABLE = "unavailable"

# --- Jurisdiction Schemas ---
class JurisdictionCreate(BaseModel):
    name: str
    state: Optional[str] = None
    county: Optional[str] = None
    type: Optional[str] = Field(None, alias="jurisdiction_type")
    fips_code: Optional[str] = None
    state_fips: Optional[str] = None
    county_fips: Optional[str] = None
    county_seat: Optional[str] = None
    api_available: Optional[bool] = False
    scraper_needed: Optional[bool] = True
    population: Optional[int] = None
    description: Optional[str] = None
    jurisdiction_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    class Config:
        allow_population_by_field_name = True

class JurisdictionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    type: Optional[str] = None
    api_available: Optional[bool] = None
    scraper_needed: Optional[bool] = None
    population: Optional[int] = None
    description: Optional[str] = None

class JurisdictionResponse(BaseModel):
    id: int
    name: str
    state: Optional[str] = None
    county: Optional[str] = None
    type: Optional[str] = Field(None, alias="jurisdiction_type")
    fips_code: Optional[str] = None
    state_fips: Optional[str] = None
    county_fips: Optional[str] = None
    county_seat: Optional[str] = None
    api_available: bool = False
    scraper_needed: bool = True
    population: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    jurisdiction_metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# --- Data Source Schemas ---
class DataSourceCreate(BaseModel):
    jurisdiction_id: int
    name: str = Field(..., alias="source_name")
    source_type: str
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    status: str = "active"
    description: Optional[str] = None

    class Config:
        allow_population_by_field_name = True

class DataSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

class DataSourceResponse(BaseModel):
    id: int
    jurisdiction_id: int
    name: str = Field(..., alias="source_name")
    source_type: str
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    status: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# --- Record Schemas ---
class RecordCreate(BaseModel):
    jurisdiction_id: int
    data_source_id: Optional[int] = None
    record_type: str
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    url: Optional[str] = None

    @validator('data', pre=True)
    def check_raw_data(cls, v, values):
        # Allow 'raw_data' as alias for 'data'/metadata if passed
        if v is None and 'raw_data' in values:
            return values['raw_data']
        return v

    class Config:
        allow_population_by_field_name = True

class RecordUpdate(BaseModel):
    data_source_id: Optional[int] = None
    record_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

class RecordResponse(BaseModel):
    id: int
    jurisdiction_id: int
    data_source_id: Optional[int] = None
    record_type: Optional[str] = None
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[date] = None
    url: Optional[str] = None
    data: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# --- Entity Schemas ---
class EntityCreate(BaseModel):
    entity_name: str
    entity_type: EntityType
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None
    jurisdiction_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True

class EntityUpdate(BaseModel):
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    description: Optional[str] = None

# --- Relationship Schemas ---
class RelationshipCreate(BaseModel):
    entity1_id: int = Field(..., alias="source_entity_id")
    entity2_id: int = Field(..., alias="target_entity_id")
    relationship_type: str
    record_id: Optional[int] = None
    role1: Optional[str] = None
    role2: Optional[str] = None
    context: Optional[str] = Field(None, description="Context of the relationship")
    evidence: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    description: Optional[str] = None

    @validator('entity1_id', pre=True)
    def check_source_entity(cls, v, values):
        if 'source_entity_id' in values:
            return values['source_entity_id']
        return v

    class Config:
        allow_population_by_field_name = True

class RelationshipUpdate(BaseModel):
    relationship_type: Optional[str] = None
    record_id: Optional[int] = None
    role1: Optional[str] = None
    role2: Optional[str] = None
    context: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

# --- Search Schemas ---
class SearchQuery(BaseModel):
    query: Optional[str] = None
    jurisdiction_ids: Optional[List[int]] = None
    record_types: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    sort_by: Optional[str] = "date"
    sort_order: Optional[str] = "desc"
    page: int = 1
    page_size: int = 50

class SearchResponse(BaseModel):
    records: List[RecordResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class ExportRequest(BaseModel):
    format: str = "json"
    query: Optional[SearchQuery] = None
    fields: Optional[List[str]] = None

# --- Coverage Schemas ---
class CoverageSummaryResponse(BaseModel):
    total_jurisdictions: int
    covered_jurisdictions: int
    coverage_percentage: float
    total_counties: int
    covered_counties: int
    total_states: int
    covered_states: int
    total_territories: int
    covered_territories: int
    data_categories: Dict[str, Dict[str, Any]]
    tier_breakdown: Dict[str, Dict[str, Any]]
    last_updated: str

class StateCoverageResponse(BaseModel):
    state_code: str
    state_name: str
    fips_code: str
    tier: int
    total_counties: int
    covered_counties: int
    coverage_percentage: float
    data_categories: Dict[str, int]
    record_count: int
    last_scraped: Optional[str]

class CoverageGapResponse(BaseModel):
    fips_code: str
    jurisdiction_name: str
    state: str
    county: Optional[str]
    population: int
    tier: int
    missing_categories: List[str]
    gap_reason: Optional[str]
    priority_score: float

class CoverageRefreshRequest(BaseModel):
    data_categories: Optional[List[str]] = None
    force_refresh: bool = False

class CoverageRefreshResponse(BaseModel):
    fips_code: str
    status: str
    message: str
    categories_queued: List[str]
    estimated_completion: Optional[str]

# --- Saved Search Schemas ---
class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    search_params: Dict[str, Any] = Field(..., description="Search parameters to save")
    notify_on_new_results: bool = False
    notification_frequency: Optional[str] = "daily"  # daily, weekly, immediate

class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    search_params: Optional[Dict[str, Any]] = None
    notify_on_new_results: Optional[bool] = None
    notification_frequency: Optional[str] = None

class SavedSearchResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    search_params: Dict[str, Any]
    last_run: Optional[str]
    run_count: int
    notify_on_new_results: bool
    notification_frequency: Optional[str]
    last_result_count: int
    created_at: str
    updated_at: str

# --- Favorites Schemas ---
class FavoriteCreate(BaseModel):
    record_id: Optional[int] = None
    entity_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator('entity_id', always=True)
    def check_one_id_provided(cls, v, values):
        record_id = values.get('record_id')
        if not record_id and not v:
            raise ValueError('Either record_id or entity_id must be provided')
        if record_id and v:
            raise ValueError('Only one of record_id or entity_id can be provided')
        return v

class FavoriteUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class FavoriteResponse(BaseModel):
    id: int
    favorite_type: str
    record: Optional[RecordResponse] = None
    # entity: Optional[EntityResponse] = None # EntityResponse not fully defined yet, can add later
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime

    class Config:
        orm_mode = True

# --- Scraper Schemas ---
class ScraperRunResponse(BaseModel):
    id: int
    data_source_id: Optional[int]
    jurisdiction_id: Optional[int]
    data_category: Optional[str]
    scraper_module: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    records_found: int
    records_new: int
    records_updated: int
    records_failed: int
    error_message: Optional[str]
    duration_seconds: Optional[int]

    class Config:
        orm_mode = True

class ScraperStatusResponse(BaseModel):
    total_runs_24h: int
    success_rate_24h: float
    active_runs: int
    failed_runs_24h: int
    recent_runs: List[ScraperRunResponse]
