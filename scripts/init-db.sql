-- DataGod Database Initialization Script
-- This script runs when the PostgreSQL container first starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Create indexes for better search performance
-- These will be created after Alembic migrations run, but we define them here for reference

-- Full-text search configuration
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS datagod_search (COPY = english);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE datagod TO datagod;

-- Create schema for DataGod
CREATE SCHEMA IF NOT EXISTS datagod;
GRANT ALL ON SCHEMA datagod TO datagod;

-- Set search path
ALTER DATABASE datagod SET search_path TO public, datagod;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'DataGod database initialized successfully';
END $$;
