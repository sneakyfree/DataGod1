# DataGod - Public Records Data Platform

[![Build Status](https://img.shields.io/github/actions/workflow/status/sneakyfree/DataGod1/ci.yml?branch=main&style=flat-square)](https://github.com/sneakyfree/DataGod1/actions)
[![Coverage](https://img.shields.io/codecov/c/github/sneakyfree/DataGod1?style=flat-square)](https://codecov.io/gh/sneakyfree/DataGod1)
[![License](https://img.shields.io/github/license/sneakyfree/DataGod1?style=flat-square)](https://github.com/sneakyfree/DataGod1/blob/main/LICENSE)
[![Version](https://img.shields.io/github/v/release/sneakyfree/DataGod1?style=flat-square)](https://github.com/sneakyfree/DataGod1/releases)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/downloads/)

DataGod is a comprehensive platform for collecting, organizing, and analyzing public records data from jurisdictions across the United States. The platform aggregates data from various sources including court records, property records, business registrations, and government databases to provide researchers, journalists, and businesses with powerful tools for data analysis.

## Features
- Comprehensive public records data collection from 10,000+ jurisdictions
- Advanced search and filtering capabilities
- Data visualization and analytics
- API access for developers
- User authentication and subscription management
- Data export functionality (CSV, JSON, Excel)
- Real-time data updates and monitoring
- Multi-source data integration (APIs, web scraping, manual uploads)
- Data quality monitoring and deduplication

## Architecture
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

## Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/datagod.git
cd datagod

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the development server
python datagod/main.py
```

## Project Structure
```
datagod/
├── api/              # FastAPI REST endpoints
├── config/           # Configuration files
├── db/               # Database related code
├── models/           # SQLAlchemy models
├── scrapers/         # Web scrapers and data collectors
├── utils/            # Utility functions
├── tests/            # Unit and integration tests
├── docs/             # Documentation
└── frontend/         # React/Next.js frontend
```

## Database Schema
The platform uses PostgreSQL with the following core tables:
- jurisdictions: Jurisdiction information (state, county, etc.)
- data_sources: Data source configuration (API endpoints, scraper settings)
- records: Public records data
- entities: Entities mentioned in records (persons, companies, properties)
- relationships: Relationships between entities
- users: User accounts and subscriptions
- subscriptions: Subscription tiers and billing

## Testing
Run unit tests:
```bash
pytest tests/
```

Run integration tests:
```bash
pytest tests/integration/
```

## Development
1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest tests/
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "Add your commit message"
   ```

5. Push to your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a pull request

## Contributing
We welcome contributions! Please read our contributing guidelines before submitting a pull request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For support, please open an issue on our GitHub repository.
