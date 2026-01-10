# DataGod API Documentation

This document provides documentation for the DataGod REST API.

## Overview

The DataGod API provides programmatic access to public records data. It follows REST conventions and returns data in JSON format.

## Authentication

All API requests require authentication via JWT tokens. To obtain a token:

1. Send a POST request to `/auth/login` with your credentials
2. Use the returned token in subsequent requests as a Bearer token in the Authorization header

Example:
```
Authorization: Bearer <your-jwt-token>
```

## Base URL

```
https://api.datagod.com/v1
```

## Endpoints

### Authentication

#### POST /auth/register
Register a new user

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer"
}
```

#### POST /auth/login
Authenticate a user

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer"
}
```

### Jurisdictions

#### GET /jurisdictions
Get a list of jurisdictions

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Number of items per page (default: 20, max: 100)
- `state` (string): Filter by state
- `county` (string): Filter by county
- `search` (string): Search term

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Los Angeles County",
      "state": "CA",
      "county": "Los Angeles",
      "type": "county",
      "api_available": true,
      "scraper_needed": false,
      "description": "Los Angeles County public records"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 10000,
    "pages": 500
  }
}
```

#### GET /jurisdictions/{id}
Get a specific jurisdiction

**Response:**
```json
{
  "id": 1,
  "name": "Los Angeles County",
  "state": "CA",
  "county": "Los Angeles",
  "type": "county",
  "api_available": true,
  "scraper_needed": false,
  "description": "Los Angeles County public records",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Data Sources

#### GET /data-sources
Get a list of data sources

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Number of items per page (default: 20, max: 100)
- `jurisdiction_id` (integer): Filter by jurisdiction
- `source_type` (string): Filter by source type (api, scraper, manual)

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "jurisdiction_id": 1,
      "source_name": "Los Angeles County Courts API",
      "source_type": "api",
      "api_endpoint": "https://api.lacounty.gov/records",
      "status": "active",
      "last_scraped": "2023-01-01T00:00:00Z",
      "description": "Official court records API"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50,
    "pages": 3
  }
}
```

### Records

#### GET /records
Get a list of records

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Number of items per page (default: 20, max: 100)
- `jurisdiction_id` (integer): Filter by jurisdiction
- `data_source_id` (integer): Filter by data source
- `search` (string): Search term in title or description
- `date_from` (date): Filter by date range
- `date_to` (date): Filter by date range

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "jurisdiction_id": 1,
      "data_source_id": 1,
      "title": "Property Transfer Document",
      "description": "Transfer of property from John Smith to Jane Doe",
      "amount": 500000.00,
      "date": "2023-01-01",
      "url": "https://lacounty.gov/records/12345",
      "data": {
        "property_address": "123 Main St, Los Angeles, CA",
        "buyer": "Jane Doe",
        "seller": "John Smith"
      },
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100000,
    "pages": 5000
  }
}
```

#### GET /records/{id}
Get a specific record

**Response:**
```json
{
  "id": 1,
  "jurisdiction_id": 1,
  "data_source_id": 1,
  "title": "Property Transfer Document",
  "description": "Transfer of property from John Smith to Jane Doe",
  "amount": 500000.00,
  "date": "2023-01-01",
  "url": "https://lacounty.gov/records/12345",
  "data": {
    "property_address": "123 Main St, Los Angeles, CA",
    "buyer": "Jane Doe",
    "seller": "John Smith"
  },
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Search

#### POST /search
Advanced search across records

**Request Body:**
```json
{
  "query": "property transfer",
  "jurisdiction_ids": [1, 2, 3],
  "date_from": "2023-01-01",
  "date_to": "2023-12-31",
  "amount_min": 100000,
  "amount_max": 1000000,
  "sort_by": "date",
  "sort_order": "desc",
  "page": 1,
  "limit": 20
}
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "jurisdiction_id": 1,
      "data_source_id": 1,
      "title": "Property Transfer Document",
      "description": "Transfer of property from John Smith to Jane Doe",
      "amount": 500000.00,
      "date": "2023-01-01",
      "url": "https://lacounty.gov/records/12345",
      "data": {
        "property_address": "123 Main St, Los Angeles, CA",
        "buyer": "Jane Doe",
        "seller": "John Smith"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### Statistics

#### GET /stats/overview
Get system overview statistics

**Response:**
```json
{
  "total_jurisdictions": 10000,
  "total_records": 1000000,
  "total_data_sources": 500,
  "active_data_sources": 450,
  "last_updated": "2023-01-01T00:00:00Z"
}
```

## Error Handling

All API errors return a JSON response with the following structure:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `VALIDATION_ERROR`: Request data validation failed
- `INTERNAL_ERROR`: Server-side error

## Rate Limiting

The API implements rate limiting:
- Free tier: 100 requests per hour
- Premium tier: 1000 requests per hour
- Admin: Unlimited

## Versioning

API versioning is handled through the base URL:
- v1: https://api.datagod.com/v1
