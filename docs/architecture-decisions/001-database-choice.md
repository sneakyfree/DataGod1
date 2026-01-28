# ADR 001: Database Choice - PostgreSQL

## Status
✅ **Accepted** - 2026-01-10

## Context

DataGod requires a robust database solution to handle public records data from 10,000+ jurisdictions with projected data volumes of 10M-1B records. The database must support:

1. **Large-scale data storage** (10M-1B records)
2. **Complex query patterns** (joins, full-text search, geospatial)
3. **High concurrency** (1,000-20,000 concurrent users)
4. **Advanced features** (JSON, arrays, full-text search)
5. **Scalability** (from launch to enterprise scale)
6. **Reliability and performance** (sub-second response times)

## Decision

**Choose PostgreSQL** as the primary database for DataGod.

## Rationale

### Evaluation Criteria

| Criteria | Weight | SQLite | PostgreSQL | Winner |
|----------|--------|--------|------------|--------|
| **Scalability** | 30% | 3/10 | 10/10 | PostgreSQL |
| **Performance** | 25% | 6/10 | 9/10 | PostgreSQL |
| **Cost** | 15% | 10/10 | 7/10 | SQLite |
| **Features** | 20% | 6/10 | 10/10 | PostgreSQL |
| **Complexity** | 10% | 9/10 | 6/10 | SQLite |
| **Total Score** | | **6.0** | **8.9** | **PostgreSQL** |

### Detailed Comparison

#### 1. Scalability
- **SQLite**: Limited to single-file database, poor concurrency, max ~10-20 connections
- **PostgreSQL**: Handles thousands of concurrent connections, horizontal scaling with read replicas
- **Winner**: PostgreSQL (critical for 10M-1B records)

#### 2. Performance
- **SQLite**: Fast for simple queries, but poor for complex joins
- **PostgreSQL**: Advanced query optimizer, better indexing, parallel query execution
- **Winner**: PostgreSQL (essential for complex public records queries)

#### 3. Features
- **SQLite**: Basic SQL support, limited data types
- **PostgreSQL**: Full-text search, JSON/JSONB, geographic data types, arrays, advanced indexing
- **Winner**: PostgreSQL (required for DataGod's search and analysis features)

#### 4. Concurrency
- **SQLite**: File-level locking, poor multi-user performance
- **PostgreSQL**: MVCC architecture, excellent concurrent read/write performance
- **Winner**: PostgreSQL (critical for multi-user platform)

#### 5. Ecosystem
- **SQLite**: Limited tooling and extensions
- **PostgreSQL**: Rich ecosystem (PostGIS, pg_partman, TimescaleDB, etc.)
- **Winner**: PostgreSQL (enables future enhancements)

### Cost Analysis

#### Initial Costs (Self-hosted)
- **SQLite**: $0 (included with Python)
- **PostgreSQL**: $0 (open source)
- **Winner**: Tie

#### Cloud Costs (AWS RDS)
- **SQLite**: Not applicable (not suitable for cloud)
- **PostgreSQL**: $100-$500/month for production workloads
- **Winner**: SQLite (but not practical for our scale)

### Implementation Strategy

#### Phase 1: Self-hosted PostgreSQL (0-50M records)
- **Hardware**: 4 vCPU, 16GB RAM, 1TB SSD
- **Cost**: $100-$200/month
- **Connections**: 50-100 connection pool
- **Backup**: Daily backups with 30-day retention

#### Phase 2: Cloud PostgreSQL (50M-1B records)
- **Service**: AWS RDS/Aurora PostgreSQL
- **Instance**: db.m5.xlarge (4 vCPU, 16GB RAM)
- **Cost**: $300-$800/month
- **Scaling**: Read replicas for read-heavy workloads

#### Phase 3: Enterprise PostgreSQL (1B+ records)
- **Service**: AWS Aurora PostgreSQL Serverless v2
- **Configuration**: Auto-scaling based on demand
- **Cost**: $1,000-$5,000/month
- **Features**: Multi-region replication, advanced monitoring

## Implementation

### Installation (Ubuntu/Debian)
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Verify installation
psql --version
```

### Configuration
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf

# Key settings
max_connections = 200
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 16MB
wal_buffers = 16MB
```

### Database Setup
```bash
# Create database and user
sudo -u postgres psql
```
```sql
CREATE DATABASE datagod;
CREATE USER datagod WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE datagod TO datagod;
ALTER DATABASE datagod OWNER TO datagod;
```

### Connection Configuration
```python
# datagod/config/settings.py
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://datagod:secure_password_here@localhost:5432/datagod"
)
```

### Connection Pooling
```python
# datagod/db/connection_pool.py
from psycopg2 import pool
from datagod.config.settings import DATABASE_URL

connection_pool = pool.SimpleConnectionPool(
    minconn=5,
    maxconn=50,
    dsn=DATABASE_URL
)

def get_connection():
    return connection_pool.getconn()

def return_connection(conn):
    connection_pool.putconn(conn)
```

## Migration Plan

### From SQLite to PostgreSQL
1. **Export SQLite data**: `sqlite3 datagod.db .dump > export.sql`
2. **Convert schema**: Use `pgloader` or custom scripts
3. **Data migration**: Transform and import data
4. **Testing**: Verify data integrity
5. **Cutover**: Switch applications to PostgreSQL

### Tools for Migration
- **pgloader**: Automated migration tool
- **SQLAlchemy**: ORM compatibility layer
- **Custom scripts**: For complex data transformations

## Monitoring and Maintenance

### Key Metrics to Monitor
- **Connection count**: Alert at 80% of pool capacity
- **Query performance**: Alert on queries >1s
- **Lock contention**: Monitor for blocking queries
- **Disk I/O**: Monitor for bottlenecks
- **Replication lag**: For read replicas

### Maintenance Tasks
- **Vacuum**: Regular table maintenance
- **Analyze**: Update statistics for query planner
- **Index maintenance**: Rebuild fragmented indexes
- **Backup verification**: Test restore procedures

## Alternatives Considered

### 1. SQLite
**Pros**: Simple, zero configuration, embedded
**Cons**: Poor scalability, limited concurrency, no advanced features
**Rejected**: Cannot handle projected data volume and user load

### 2. MySQL/MariaDB
**Pros**: Widely used, good performance, mature ecosystem
**Cons**: Less advanced features than PostgreSQL, licensing concerns
**Rejected**: PostgreSQL offers better features for our use case

### 3. MongoDB
**Pros**: Flexible schema, good for unstructured data
**Cons**: Not ideal for relational data, complex transactions
**Rejected**: DataGod requires strong relational capabilities

### 4. AWS DynamoDB
**Pros**: Serverless, auto-scaling, managed service
**Cons**: Expensive at scale, limited query capabilities
**Rejected**: Cost prohibitive and query limitations

## Success Metrics

### Technical Metrics
- **Uptime**: >99.9% availability
- **Query Performance**: <500ms for 95% of queries
- **Concurrency**: Support 1,000+ concurrent users
- **Scalability**: Handle 10M-1B records efficiently

### Operational Metrics
- **Backup Success Rate**: 100% successful daily backups
- **Restore Time**: <30 minutes for full restore
- **Maintenance Window**: <1 hour per month

## Risks and Mitigations

### Risks
1. **Migration Complexity**: Data migration from existing systems
2. **Performance Tuning**: Requires expertise for optimization
3. **Cost Growth**: Cloud costs increase with scale
4. **Operational Overhead**: Requires DBA expertise

### Mitigations
1. **Phased Migration**: Gradual transition with testing
2. **Performance Monitoring**: Continuous optimization
3. **Cost Management**: Start self-hosted, migrate to cloud when needed
4. **Training**: Invest in team PostgreSQL expertise

## Conclusion

PostgreSQL is the optimal choice for DataGod's database requirements, offering the best combination of scalability, performance, and features needed to support the platform's growth from launch to enterprise scale. The decision provides a solid foundation for handling 10M-1B public records while supporting complex search, analysis, and reporting features.

**Next Steps**:
1. ✅ Implement PostgreSQL installation and configuration
2. ✅ Set up connection pooling and monitoring
3. ✅ Develop migration plan from existing data sources
4. ✅ Implement backup and disaster recovery procedures
5. ✅ Train team on PostgreSQL best practices

**Decision Date**: 2026-01-10
**Decision Owner**: DataGod Architecture Team
**Status**: Active
**Review Date**: 2026-07-10 (6 months)