# DataGod Documentation

Welcome to the DataGod documentation. This is the central hub for all project documentation, guides, and resources.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Architecture](#architecture)
4. [API Documentation](#api-documentation)
5. [Database Schema](#database-schema)
6. [Deployment](#deployment)
7. [Development](#development)
8. [User Guide](#user-guide)

## Overview

DataGod is a comprehensive platform for collecting, organizing, and analyzing public records data from jurisdictions across the United States. The platform aggregates data from various sources including court records, property records, business registrations, and government databases to provide researchers, journalists, and businesses with powerful tools for data analysis.

## Getting Started

To get started with DataGod, follow these steps:

1. Clone the repository
2. Set up a virtual environment
3. Install dependencies
4. Run database migrations
5. Start the development server

## Architecture

DataGod follows a modular architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer     │    │   Data Layer    │
│  (React/Next.js)│───▶│  (FastAPI)      │───▶│  (PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scrapers      │    │   Data Pipeline │    │   Data Sources  │
│  (Python)       │    │  (ETL)          │    │  (APIs, Web)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## API Documentation

API documentation is available at `/docs` when running the application locally.

## Database Schema

The platform uses PostgreSQL with the following core tables:
- jurisdictions: Jurisdiction information (state, county, etc.)
- data_sources: Data source configuration (API endpoints, scraper settings)
- records: Public records data
- entities: Entities mentioned in records (persons, companies, properties)
- relationships: Relationships between entities
- users: User accounts and subscriptions
- subscriptions: Subscription tiers and billing

## Deployment

DataGod can be deployed to various cloud platforms including AWS, GCP, and Azure.

## Development

For development guidelines, please see the [Development Guide](development.md).

## User Guide

For end-user documentation, please see the [User Guide](user-guide.md).
