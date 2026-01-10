# DataGod API Documentation

## Overview

DataGod provides a comprehensive REST API for accessing property records, public data, and analytics across all 50 US states, DC, and 5 territories.

**Base URL:** `https://api.datagod.io/api/v2`

**Authentication:** Bearer token via `Authorization` header

---

## Authentication

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "role": "user"
  }
}
```

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "secure_password",
  "name": "New User"
}
```

---

## Jurisdictions

### List Jurisdictions
```http
GET /jurisdictions
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | string | Filter by state code (e.g., "CA") |
| `type` | string | Filter by type ("county", "city", "state") |
| `page` | int | Page number (default: 1) |
| `per_page` | int | Results per page (default: 20, max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Los Angeles County",
      "state": "CA",
      "type": "county",
      "api_available": true,
      "scraper_needed": false,
      "population": 10014009,
      "data_sources": ["property", "deed", "court"]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 3243,
    "total_pages": 163
  }
}
```

### Get Jurisdiction
```http
GET /jurisdictions/{id}
```

**Response:**
```json
{
  "id": 1,
  "name": "Los Angeles County",
  "state": "CA",
  "type": "county",
  "api_available": true,
  "scraper_needed": false,
  "population": 10014009,
  "data_sources": [
    {
      "id": 1,
      "name": "LA County Assessor API",
      "type": "api",
      "status": "active",
      "last_sync": "2025-12-31T10:00:00Z"
    }
  ],
  "coverage_stats": {
    "property_records": 2500000,
    "deed_records": 1800000,
    "court_records": 500000,
    "last_updated": "2025-12-31T10:00:00Z"
  }
}
```

---

## Properties

### Search Properties
```http
GET /properties/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `address` | string | Street address |
| `city` | string | City name |
| `state` | string | State code |
| `zip_code` | string | ZIP code |
| `parcel_id` | string | Parcel/APN number |
| `owner_name` | string | Owner name search |
| `min_value` | number | Minimum assessed value |
| `max_value` | number | Maximum assessed value |
| `page` | int | Page number |
| `per_page` | int | Results per page |

**Response:**
```json
{
  "data": [
    {
      "id": "CA-LA-123456789",
      "parcel_id": "123-456-789",
      "address": "123 Main Street",
      "city": "Los Angeles",
      "state": "CA",
      "zip_code": "90001",
      "owner": {
        "name": "John Doe",
        "mailing_address": "456 Oak Ave, Los Angeles, CA 90002"
      },
      "property_info": {
        "type": "Single Family Residential",
        "bedrooms": 3,
        "bathrooms": 2,
        "square_feet": 1850,
        "lot_size": 6500,
        "year_built": 1985
      },
      "valuation": {
        "assessed_value": 750000,
        "land_value": 500000,
        "improvement_value": 250000,
        "tax_year": 2025
      },
      "jurisdiction_id": 1,
      "last_updated": "2025-12-31T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150
  }
}
```

### Get Property by ID
```http
GET /properties/{id}
```

### Get Property History
```http
GET /properties/{id}/history
```

**Response:**
```json
{
  "property_id": "CA-LA-123456789",
  "sales_history": [
    {
      "date": "2020-05-15",
      "sale_price": 650000,
      "buyer": "John Doe",
      "seller": "Jane Smith",
      "document_number": "2020-0500000"
    }
  ],
  "assessment_history": [
    {
      "year": 2025,
      "assessed_value": 750000
    },
    {
      "year": 2024,
      "assessed_value": 700000
    }
  ],
  "permit_history": [
    {
      "date": "2019-03-10",
      "type": "Building Permit",
      "description": "Kitchen remodel",
      "value": 25000,
      "status": "Completed"
    }
  ]
}
```

---

## Deeds & Documents

### Search Deeds
```http
GET /deeds/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `jurisdiction_id` | int | Jurisdiction ID |
| `grantor` | string | Grantor name |
| `grantee` | string | Grantee name |
| `document_type` | string | Type (deed, mortgage, lien) |
| `start_date` | date | Start of date range |
| `end_date` | date | End of date range |
| `parcel_id` | string | Associated parcel |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "document_number": "2025-0001234",
      "document_type": "Grant Deed",
      "recording_date": "2025-01-15",
      "grantor": "Jane Smith",
      "grantee": "John Doe",
      "consideration": 650000,
      "parcel_ids": ["123-456-789"],
      "jurisdiction_id": 1,
      "pdf_url": "/documents/2025-0001234.pdf"
    }
  ]
}
```

---

## Court Records

### Search Court Cases
```http
GET /court-records/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `jurisdiction_id` | int | Jurisdiction ID |
| `party_name` | string | Party name |
| `case_type` | string | civil, criminal, family, probate |
| `case_number` | string | Case number |
| `start_date` | date | Filing start date |
| `end_date` | date | Filing end date |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "case_number": "2025-CV-001234",
      "case_type": "civil",
      "case_title": "Doe v. Smith",
      "filing_date": "2025-01-10",
      "status": "Open",
      "parties": [
        {"name": "John Doe", "role": "Plaintiff"},
        {"name": "Jane Smith", "role": "Defendant"}
      ],
      "jurisdiction_id": 1
    }
  ]
}
```

---

## Business Filings

### Search Businesses
```http
GET /businesses/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Business name |
| `state` | string | State of incorporation |
| `entity_type` | string | LLC, Corporation, etc. |
| `status` | string | active, inactive, dissolved |
| `agent_name` | string | Registered agent |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "entity_name": "Acme Corporation",
      "entity_type": "Corporation",
      "state": "DE",
      "status": "Active",
      "formation_date": "2010-03-15",
      "registered_agent": {
        "name": "CT Corporation",
        "address": "1209 Orange St, Wilmington, DE 19801"
      },
      "officers": [
        {"name": "John Doe", "title": "CEO"},
        {"name": "Jane Smith", "title": "CFO"}
      ],
      "filing_number": "12345678"
    }
  ]
}
```

---

## Professional Licenses

### Search Licenses
```http
GET /licenses/search
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Licensee name |
| `license_type` | string | real_estate, contractor, etc. |
| `license_number` | string | License number |
| `state` | string | State |
| `status` | string | active, expired, suspended |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "licensee_name": "John Doe",
      "license_type": "Real Estate Broker",
      "license_number": "01234567",
      "state": "CA",
      "status": "Active",
      "issue_date": "2015-06-01",
      "expiration_date": "2026-05-31",
      "disciplinary_actions": []
    }
  ]
}
```

---

## Data Validation

### Validate Record
```http
POST /validate
Content-Type: application/json

{
  "record_type": "property",
  "data": {
    "parcel_id": "123-456-789",
    "address": "123 Main Street",
    "city": "Springfield",
    "state": "IL",
    "zip_code": "62701",
    "assessed_value": 150000
  }
}
```

**Response:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [
    {
      "field": "year_built",
      "message": "Recommended field not provided"
    }
  ],
  "quality_score": {
    "completeness": 85.0,
    "accuracy": 100.0,
    "overall": 92.5
  }
}
```

---

## Monitoring & Dashboard

### Get Dashboard Data
```http
GET /dashboard/quality
```

**Response:**
```json
{
  "timestamp": "2025-12-31T19:00:00Z",
  "overview": {
    "states_covered": 56,
    "total_states": 56,
    "coverage_percent": 100.0,
    "total_records": 50000000,
    "jurisdictions_tracked": 3243
  },
  "coverage": {
    "by_state": {
      "CA": {
        "county_count": 58,
        "total_records": 5000000,
        "avg_coverage_percent": 95.5,
        "has_coverage": true
      }
    },
    "heatmap_data": {
      "CA": 95.5,
      "TX": 92.0
    }
  },
  "quality": {
    "dataset_count": 100,
    "avg_score": 88.5,
    "grade_distribution": {"A": 45, "B": 35, "C": 15, "D": 5}
  },
  "errors": {
    "total_errors": 150,
    "unresolved_count": 12,
    "by_type": {"timeout": 5, "parse": 4, "auth": 3}
  },
  "quotas": {
    "api_count": 5,
    "critical_count": 0,
    "warning_count": 1
  }
}
```

### Get Scraper Health
```http
GET /health/scrapers
```

**Response:**
```json
{
  "overall_status": "healthy",
  "scrapers": [
    {
      "id": "california_api",
      "status": "healthy",
      "success_rate": 99.5,
      "avg_response_time_ms": 250,
      "last_success": "2025-12-31T18:55:00Z",
      "quota_usage_percent": 45.0
    }
  ]
}
```

### Get Metrics
```http
GET /metrics
```

Returns Prometheus-compatible metrics.

---

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}
```

**Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## Rate Limiting

| Plan | Requests/Hour | Requests/Day |
|------|---------------|--------------|
| Free | 100 | 1,000 |
| Basic | 1,000 | 10,000 |
| Pro | 10,000 | 100,000 |
| Enterprise | Unlimited | Unlimited |

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time until reset (Unix timestamp)

---

## Webhooks

Configure webhooks to receive real-time notifications:

```http
POST /webhooks
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["record.created", "record.updated", "scraper.error"],
  "secret": "your_webhook_secret"
}
```

**Webhook Payload:**
```json
{
  "event": "record.created",
  "timestamp": "2025-12-31T19:00:00Z",
  "data": {
    "record_id": "CA-LA-123456789",
    "record_type": "property",
    "jurisdiction_id": 1
  },
  "signature": "sha256=..."
}
```

---

## SDK Examples

### Python
```python
from datagod import DataGodClient

client = DataGodClient(api_key="your_api_key")

# Search properties
properties = client.properties.search(
    address="123 Main St",
    city="Los Angeles",
    state="CA"
)

# Get property details
property = client.properties.get("CA-LA-123456789")

# Search court records
cases = client.court_records.search(
    party_name="John Doe",
    case_type="civil"
)
```

### JavaScript
```javascript
import { DataGodClient } from '@datagod/sdk';

const client = new DataGodClient({ apiKey: 'your_api_key' });

// Search properties
const properties = await client.properties.search({
  address: '123 Main St',
  city: 'Los Angeles',
  state: 'CA',
});

// Get property details
const property = await client.properties.get('CA-LA-123456789');
```

---

## Changelog

### v2.0.0 (2025-12-31)
- Added all 56 jurisdictions (50 states + DC + 5 territories)
- Added court records, business filings, professional licenses
- Added data quality dashboard
- Added real-time monitoring
- Improved rate limiting

### v1.0.0 (2025-01-01)
- Initial release with 14 states
- Property and deed records
