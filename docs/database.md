# DataGod Database Schema

This document describes the database schema for the DataGod platform.

## Overview

DataGod uses PostgreSQL as its primary database system. The schema is designed to support efficient storage, retrieval, and querying of public records data from thousands of jurisdictions.

## Core Tables

### jurisdictions

Stores information about jurisdictions (counties, cities, states, etc.)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| name | varchar(255) | NO | Jurisdiction name |
| state | varchar(2) | YES | Two-letter state code |
| county | varchar(100) | YES | County name |
| type | varchar(50) | YES | Jurisdiction type (county, city, state, etc.) |
| api_available | boolean | YES | Whether API is available |
| scraper_needed | boolean | YES | Whether scraping is needed |
| description | text | YES | Description of jurisdiction |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### data_sources

Stores information about data sources for each jurisdiction

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| jurisdiction_id | integer | NO | Foreign key to jurisdictions |
| source_name | varchar(255) | NO | Name of data source |
| source_type | varchar(50) | NO | Type of source (api, scraper, manual) |
| api_endpoint | varchar(500) | YES | API endpoint URL |
| status | varchar(50) | YES | Status (active, inactive, error) |
| last_scraped | timestamp | YES | Last time data was scraped |
| description | text | YES | Description of data source |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### records

Stores the actual public records data

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| jurisdiction_id | integer | NO | Foreign key to jurisdictions |
| data_source_id | integer | NO | Foreign key to data_sources |
| title | varchar(500) | NO | Record title |
| description | text | YES | Record description |
| amount | numeric | YES | Monetary amount if applicable |
| date | date | YES | Date of record |
| url | varchar(1000) | YES | URL to original record |
| data | jsonb | YES | Additional structured data |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### entities

Stores entities mentioned in records (persons, companies, properties, etc.)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| entity_name | varchar(500) | NO | Name of entity |
| entity_type | varchar(100) | NO | Type of entity (person, company, property, etc.) |
| entity_id | varchar(255) | YES | External ID if available |
| data | jsonb | YES | Additional structured data |
| description | text | YES | Description of entity |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### relationships

Stores relationships between entities

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| entity1_id | integer | NO | First entity ID |
| entity2_id | integer | NO | Second entity ID |
| relationship_type | varchar(100) | NO | Type of relationship |
| metadata | jsonb | YES | Additional relationship metadata |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### users

Stores user information

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| email | varchar(255) | NO | User email |
| password_hash | varchar(255) | NO | Hashed password |
| name | varchar(255) | YES | User name |
| is_active | boolean | YES | Whether user is active |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### subscriptions

Stores subscription information for users

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| user_id | integer | NO | Foreign key to users |
| subscription_type | varchar(50) | NO | Subscription tier |
| status | varchar(50) | YES | Subscription status |
| start_date | date | YES | Subscription start date |
| end_date | date | YES | Subscription end date |
| created_at | timestamp | NO | Creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

## Indexes

### jurisdictions
- `idx_jurisdiction_state_county` on (state, county)

### records
- `idx_record_jurisdiction` on (jurisdiction_id)
- `idx_record_data_source` on (data_source_id)
- `idx_record_date` on (date)

### entities
- `idx_entity_name_type` on (entity_name, entity_type)
- `idx_entity_id` on (entity_id)

### relationships
- `idx_relationship_entities` on (entity1_id, entity2_id)
- `idx_relationship_type` on (relationship_type)

## Relationships

1. `jurisdictions` ↔ `data_sources` (one-to-many)
2. `jurisdictions` ↔ `records` (one-to-many)
3. `data_sources` ↔ `records` (one-to-many)
4. `entities` ↔ `records` (many-to-many through relationship table)
5. `users` ↔ `subscriptions` (one-to-many)

## Migration Strategy

Data migrations are handled using Alembic. All schema changes should be implemented through migration scripts to ensure consistency across environments.

## Data Quality

- All tables have `created_at` and `updated_at` timestamps
- Foreign key constraints are enforced
- Data validation is performed at the application level
- Regular data quality checks are implemented
