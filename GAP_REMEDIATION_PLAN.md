# DataGod Gap Remediation Plan
## Comprehensive Action Plan Based on Gap Analysis

**Created:** January 1, 2026
**Current Test Coverage:** 53% (5715 tests, 8 failures)
**Target Coverage:** 90%+
**Estimated Total Tasks:** 127 discrete work items

---

# PHASE 1: CRITICAL BLOCKERS (Must Fix Before Any Use)
**Priority:** CRITICAL | **Estimated Items:** 12

## 1.1 Database Migration - Users Table [BLOCKER]
**Issue:** User model defined but no Alembic migration exists
**Impact:** Authentication will fail in production

### Tasks:
- [ ] **1.1.1** Create Alembic migration for users table with all 20+ columns
- [ ] **1.1.2** Add indexes for username, email, subscription_tier
- [ ] **1.1.3** Add foreign key constraints and relationships
- [ ] **1.1.4** Test migration upgrade/downgrade cycle
- [ ] **1.1.5** Verify user authentication works after migration

**Files to create/modify:**
- `datagod/migrations/versions/XXXX_create_users_table.py`

---

## 1.2 API CRUD Validation Failures [BLOCKER]
**Issue:** All POST operations return 422 Unprocessable Entity
**Impact:** Cannot create any data through API

### Tasks:
- [ ] **1.2.1** Fix JurisdictionCreate Pydantic schema validation
  - File: `api/src/api_v2.py` or `api/src/api_v2_simple.py`
  - Issue: Request body schema mismatch

- [ ] **1.2.2** Fix DataSourceCreate Pydantic schema validation
  - Ensure all required fields have defaults or are optional

- [ ] **1.2.3** Fix RecordCreate Pydantic schema validation
  - Check date format validators
  - Verify JSON field handling

- [ ] **1.2.4** Fix EntityCreate Pydantic schema validation
  - Validate entity_type enum values

- [ ] **1.2.5** Fix RelationshipCreate Pydantic schema validation
  - Verify entity_id references work correctly

- [ ] **1.2.6** Add comprehensive request/response schema tests
- [ ] **1.2.7** Verify all 8 failing tests pass after fixes

**Files to modify:**
- `api/src/api_v2.py` (lines 577-1022)
- `api/src/schemas.py` (if exists) or create Pydantic models

---

## 1.3 Search/Export Response Schema [BLOCKER]
**Issue:** Response missing 'id' field, causing KeyError
**Impact:** Search and export features broken

### Tasks:
- [ ] **1.3.1** Fix advanced_search response to include record IDs
  - File: `api/src/api_v2.py` (lines 1024-1078)

- [ ] **1.3.2** Fix export_data response schema
  - File: `api/src/api_v2.py` (lines 1079-1180)

- [ ] **1.3.3** Add response model validation tests
- [ ] **1.3.4** Verify test_advanced_search passes
- [ ] **1.3.5** Verify test_data_export passes

---

# PHASE 2: HIGH PRIORITY - Core Functionality
**Priority:** HIGH | **Estimated Items:** 28

## 2.1 Scraper CLI Implementation
**Issue:** CLI shows "Scraper functionality not yet fully implemented"
**Impact:** Core data collection feature non-functional

### Tasks:
- [ ] **2.1.1** Implement scraper command in cli.py (line 93)
- [ ] **2.1.2** Add jurisdiction selection logic
- [ ] **2.1.3** Add data source discovery
- [ ] **2.1.4** Implement progress reporting
- [ ] **2.1.5** Add error handling and retry logic
- [ ] **2.1.6** Create CLI tests for scraper commands
- [ ] **2.1.7** Document scraper CLI usage

**Files to modify:**
- `cli.py` (lines 90-150)

---

## 2.2 Database Manager Test Coverage (80% → 95%)
**Issue:** Critical CRUD methods untested
**Impact:** Data integrity at risk

### Tasks:
- [ ] **2.2.1** Test session management (lines 95-97, 110-112)
- [ ] **2.2.2** Test transaction rollback scenarios (lines 124, 171-173)
- [ ] **2.2.3** Test bulk operations (lines 183-185, 195-197)
- [ ] **2.2.4** Test search/filter methods (lines 241-243, 271-273)
- [ ] **2.2.5** Test relationship CRUD (lines 287-289, 299-301)
- [ ] **2.2.6** Test user authentication methods (lines 892-930)
- [ ] **2.2.7** Test password reset flow (lines 1010-1047)
- [ ] **2.2.8** Test email verification (lines 1080-1128)

**Files to modify:**
- `tests/test_db_manager_extended.py`

---

## 2.3 Main Application Entry Point (5% → 90%)
**Issue:** Core data collection pipeline untested
**Impact:** Cannot verify application works

### Tasks:
- [ ] **2.3.1** Create test file for main.py
- [ ] **2.3.2** Test initialization (lines 11-30)
- [ ] **2.3.3** Test configuration loading (lines 31-50)
- [ ] **2.3.4** Test data pipeline startup (lines 51-100)
- [ ] **2.3.5** Test graceful shutdown (lines 101-156)
- [ ] **2.3.6** Mock external dependencies for unit tests

**Files to create:**
- `tests/test_main.py`

---

## 2.4 Stripe Payment Integration (62% → 95%)
**Issue:** Payment webhook handling untested
**Impact:** Revenue collection unreliable

### Tasks:
- [ ] **2.4.1** Test subscription creation (lines 31-33)
- [ ] **2.4.2** Test payment processing (lines 73-88)
- [ ] **2.4.3** Test webhook signature verification (lines 120-136)
- [ ] **2.4.4** Test subscription upgrade/downgrade (lines 159-167)
- [ ] **2.4.5** Test cancellation flow (lines 182-194)
- [ ] **2.4.6** Test error handling for Stripe exceptions (lines 210-253)
- [ ] **2.4.7** Add mock Stripe responses for testing

**Files to modify:**
- `tests/test_stripe_service.py` (create if missing)

---

## 2.5 Migration Environment (0% → 100%)
**Issue:** Database initialization code completely untested
**Impact:** Deployment failures possible

### Tasks:
- [ ] **2.5.1** Test offline migration mode
- [ ] **2.5.2** Test online migration mode
- [ ] **2.5.3** Test context configuration
- [ ] **2.5.4** Test migration version tracking
- [ ] **2.5.5** Test upgrade/downgrade operations

**Files to create:**
- `tests/test_migrations/test_env.py`

---

# PHASE 3: MEDIUM PRIORITY - Feature Completion
**Priority:** MEDIUM | **Estimated Items:** 45

## 3.1 State Scraper APIs (19-40% → 85%)
**Issue:** 56 state scrapers have incomplete exception handling

### Tasks (Template for each state):
For each state scraper (ak, al, ar, as, az, ca, co, ct, dc, de, fl, ga, gu, hi, ia, id, il, in, ks, ky, la, ma, md, me, mi, mn, mo, mp, ms, mt, nc, nd, ne, nh, nj, nm, nv, ny, oh, ok, or, pa, pr, ri, sc, sd, tn, tx, ut, va, vi, vt, wa, wi, wv, wy):

- [ ] **3.1.X.1** Replace pass statements with proper error logging
- [ ] **3.1.X.2** Add retry logic for transient failures
- [ ] **3.1.X.3** Add rate limiting compliance
- [ ] **3.1.X.4** Add response parsing tests
- [ ] **3.1.X.5** Add integration tests with mock responses

**Batch approach:** Create parameterized test template that tests all state scrapers

**Files to create:**
- `tests/test_scrapers/test_state_scrapers_comprehensive.py`

---

## 3.2 Machine Learning Coverage (73-77% → 90%)

### Neural Network Module Tasks:
- [ ] **3.2.1** Test model initialization variations (lines 193-195)
- [ ] **3.2.2** Test forward pass edge cases (lines 208-270)
- [ ] **3.2.3** Test training loop (lines 284-286)
- [ ] **3.2.4** Test prediction methods (lines 302-319)
- [ ] **3.2.5** Test model save/load (lines 335-337)
- [ ] **3.2.6** Test data preprocessing (lines 347-368)
- [ ] **3.2.7** Test feature extraction (lines 388-390)
- [ ] **3.2.8** Test batch processing (lines 445-494)

### Data Gathering NN Tasks:
- [ ] **3.2.9** Test data collection pipeline (lines 141-146)
- [ ] **3.2.10** Test entity extraction (lines 225-298)
- [ ] **3.2.11** Test relationship inference (lines 302-335)
- [ ] **3.2.12** Test quality scoring (lines 339-391)
- [ ] **3.2.13** Test deduplication integration (lines 425-478)
- [ ] **3.2.14** Test output formatting (lines 507-615)

**Files to modify:**
- `tests/test_ml/test_neural_network_coverage.py`
- `tests/test_ml/test_data_gathering_nn.py` (create)

---

## 3.3 Monitoring & Alerting (72-86% → 95%)

### Alerts Module Tasks:
- [ ] **3.3.1** Test alert thresholds (line 131)
- [ ] **3.3.2** Test notification dispatch (line 154)
- [ ] **3.3.3** Test escalation logic (lines 182-199)
- [ ] **3.3.4** Test alert suppression (lines 217-250)
- [ ] **3.3.5** Test recovery detection (lines 374-375)
- [ ] **3.3.6** Test alert history (lines 397-413)

### Monitoring Middleware Tasks:
- [ ] **3.3.7** Test request tracking (lines 23-27)
- [ ] **3.3.8** Test health check endpoint (lines 180-285)
- [ ] **3.3.9** Test metrics collection (line 298)
- [ ] **3.3.10** Test performance logging (lines 307-393)

**Files to modify:**
- `tests/test_monitoring/test_alerts.py`
- `tests/test_monitoring/test_middleware.py` (create)

---

## 3.4 API Test Coverage (48-57% → 90%)

### API v2 Test Tasks:
- [ ] **3.4.1** Test authentication edge cases (lines 78-131)
- [ ] **3.4.2** Test authorization/role checks (lines 187-191)
- [ ] **3.4.3** Test pagination (lines 298-358)
- [ ] **3.4.4** Test filtering (lines 363-476)
- [ ] **3.4.5** Test sorting (lines 481-604)
- [ ] **3.4.6** Test bulk operations (lines 612-732)
- [ ] **3.4.7** Test error responses (lines 740-988)

### API v2 Simple Test Tasks:
- [ ] **3.4.8** Test rate limiting (lines 89-137)
- [ ] **3.4.9** Test caching behavior (lines 143-216)
- [ ] **3.4.10** Test CORS handling (lines 239-269)
- [ ] **3.4.11** Test file uploads (lines 342-421)
- [ ] **3.4.12** Test webhook endpoints (lines 493-594)

**Files to modify:**
- `api/src/test_api_v2.py`
- `tests/test_api/test_api_comprehensive.py` (create)

---

## 3.5 Utility Module Coverage

### Caching (91% → 100%):
- [ ] **3.5.1** Test cache invalidation (lines 391-421)
- [ ] **3.5.2** Test TTL expiration
- [ ] **3.5.3** Test cache size limits

### Data Deduplication (84% → 95%):
- [ ] **3.5.4** Test fuzzy matching edge cases
- [ ] **3.5.5** Test merge strategies
- [ ] **3.5.6** Test conflict resolution

### Async Utils:
- [ ] **3.5.7** Test concurrent operations (line 586)
- [ ] **3.5.8** Test timeout handling
- [ ] **3.5.9** Test retry mechanisms

---

# PHASE 4: CODE QUALITY & DOCUMENTATION
**Priority:** LOW | **Estimated Items:** 20

## 4.1 Replace Empty Exception Handlers

### Tasks:
- [ ] **4.1.1** Add logging to all `except: pass` blocks
- [ ] **4.1.2** Add specific exception types where possible
- [ ] **4.1.3** Add metrics for exception frequency
- [ ] **4.1.4** Create exception handling guidelines

**Files affected:** All 56 state scrapers, paid API scrapers

---

## 4.2 Add Missing Docstrings

### Tasks:
- [ ] **4.2.1** Document all public API endpoints
- [ ] **4.2.2** Document all Pydantic models
- [ ] **4.2.3** Document scraper methods
- [ ] **4.2.4** Document ML pipeline steps
- [ ] **4.2.5** Generate API documentation from docstrings

---

## 4.3 Schema Consolidation

### Tasks:
- [ ] **4.3.1** Merge two-phase migrations into single comprehensive migration
- [ ] **4.3.2** Verify table names match SQLAlchemy model __tablename__
- [ ] **4.3.3** Add migration tests
- [ ] **4.3.4** Document migration strategy

---

## 4.4 Configuration Cleanup

### Tasks:
- [ ] **4.4.1** Replace Stripe placeholder values with env vars
- [ ] **4.4.2** Add configuration validation on startup
- [ ] **4.4.3** Document all required environment variables
- [ ] **4.4.4** Create .env.example file

---

# PHASE 5: INTEGRATION & E2E TESTING
**Priority:** LOW | **Estimated Items:** 15

## 5.1 End-to-End Test Suite

### Tasks:
- [ ] **5.1.1** Create E2E test for user registration → login → data access
- [ ] **5.1.2** Create E2E test for data collection pipeline
- [ ] **5.1.3** Create E2E test for search → export workflow
- [ ] **5.1.4** Create E2E test for subscription → payment → access
- [ ] **5.1.5** Create E2E test for admin operations

---

## 5.2 Performance Testing

### Tasks:
- [ ] **5.2.1** Load test API endpoints
- [ ] **5.2.2** Test database query performance
- [ ] **5.2.3** Test scraper throughput
- [ ] **5.2.4** Test ML inference latency
- [ ] **5.2.5** Document performance benchmarks

---

# EXECUTION SUMMARY

## Task Count by Phase:
| Phase | Priority | Tasks | Est. Hours |
|-------|----------|-------|------------|
| Phase 1 | CRITICAL | 12 | 8-12 |
| Phase 2 | HIGH | 28 | 20-30 |
| Phase 3 | MEDIUM | 45 | 30-40 |
| Phase 4 | LOW | 20 | 10-15 |
| Phase 5 | LOW | 15 | 10-15 |
| **TOTAL** | | **120** | **78-112** |

## Autonomous Execution Strategy

For autonomous execution, work should proceed in this order:

### Batch 1: Critical Fixes (Can run autonomously)
1. Fix all Pydantic schema validation issues (1.2.1-1.2.7)
2. Fix search/export response schemas (1.3.1-1.3.5)
3. Create users table migration (1.1.1-1.1.5)

### Batch 2: Test Coverage Push (Can run autonomously)
1. Create parameterized state scraper tests (covers 56 modules)
2. Add db_manager tests (8 tasks)
3. Add main.py tests (6 tasks)
4. Add ML module tests (14 tasks)

### Batch 3: Feature Completion (May need guidance)
1. Implement scraper CLI
2. Complete Stripe integration
3. Add monitoring tests

### Batch 4: Polish (Can run autonomously)
1. Fix exception handlers
2. Add docstrings
3. Consolidate migrations

---

# SUCCESS CRITERIA

## Phase 1 Complete When:
- [ ] All 8 failing API tests pass
- [ ] Users table migration exists and works
- [ ] Can create/read/update/delete all entity types via API

## Phase 2 Complete When:
- [ ] Test coverage reaches 75%
- [ ] CLI scraper command works
- [ ] Stripe webhooks tested
- [ ] main.py coverage > 90%

## Phase 3 Complete When:
- [ ] Test coverage reaches 85%
- [ ] All state scrapers have error handling
- [ ] ML modules > 90% coverage
- [ ] Monitoring > 95% coverage

## Phase 4 Complete When:
- [ ] No empty exception handlers
- [ ] All public APIs documented
- [ ] Single consolidated migration file
- [ ] Configuration validated

## Phase 5 Complete When:
- [ ] E2E tests pass
- [ ] Performance benchmarks documented
- [ ] Ready for production deployment
