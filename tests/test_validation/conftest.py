"""
Shared fixtures for validation tests.
"""

import pytest
from datetime import date, datetime


@pytest.fixture
def valid_property_record():
    """Valid property record for testing"""
    return {
        "parcel_id": "123-456-789",
        "address": "123 Main Street",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "county": "Sangamon",
        "property_type": "SFR",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "square_feet": 1800.0,
        "year_built": 1995,
        "assessed_value": 185000.00,
        "market_value": 225000.00,
        "owner_name": "John Smith",
        "latitude": 39.7817,
        "longitude": -89.6501,
    }


@pytest.fixture
def valid_deed_record():
    """Valid deed record for testing"""
    return {
        "document_number": "2024-001234",
        "document_type": "DEED",
        "recording_date": "2024-01-15",
        "grantor": "Jane Doe",
        "grantee": "John Smith",
        "consideration": 250000.00,
        "parcel_id": "123-456-789",
        "book": "1234",
        "page": "567",
        "county": "Sangamon",
        "state": "IL",
    }


@pytest.fixture
def valid_court_case_record():
    """Valid court case record for testing"""
    return {
        "case_number": "2024-CV-00123",
        "case_type": "CIVIL",
        "court_name": "Circuit Court of Sangamon County",
        "filing_date": "2024-01-10",
        "case_status": "OPEN",
        "case_title": "Smith v. Jones",
        "plaintiff": "John Smith",
        "defendant": "Robert Jones",
        "amount_claimed": 50000.00,
        "county": "Sangamon",
        "state": "IL",
    }


@pytest.fixture
def valid_business_entity_record():
    """Valid business entity record for testing"""
    return {
        "entity_id": "L12345678",
        "entity_name": "Acme Corporation",
        "entity_type": "CORPORATION",
        "status": "ACTIVE",
        "formation_date": "2020-05-15",
        "state": "IL",
        "ein": "12-3456789",
        "registered_agent": "CT Corporation",
        "registered_address": "123 State St, Springfield, IL 62701",
        "principal_address": "456 Commerce Way, Chicago, IL 60601",
    }


@pytest.fixture
def valid_person_record():
    """Valid person record for testing"""
    return {
        "person_id": "P001234",
        "first_name": "John",
        "last_name": "Smith",
        "middle_name": "Robert",
        "suffix": "JR",
        "date_of_birth": "1980-05-15",
        "address": "123 Main Street",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "phone": "2175551234",
        "email": "john.smith@example.com",
    }


@pytest.fixture
def sample_records_batch():
    """Batch of sample property records for testing"""
    return [
        {
            "parcel_id": "001-001-001",
            "address": "100 First Street",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701",
        },
        {
            "parcel_id": "002-002-002",
            "address": "200 Second Avenue",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60601",
        },
        {
            "parcel_id": "003-003-003",
            "address": "300 Third Boulevard",
            "city": "Peoria",
            "state": "IL",
            "zip_code": "61602",
        },
    ]
