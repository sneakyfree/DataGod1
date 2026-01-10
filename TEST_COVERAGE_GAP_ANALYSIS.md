# Test Coverage Gap Analysis

**Generated:** 2026-01-05
**Current Coverage:** 72% (24,575 statements, 6,873 missing)
**Tests:** 7,064 passed, 42 failed, 35 skipped

---

## Executive Summary

The DataGod project has achieved 72% test coverage with 7,064 passing tests. This analysis identifies the remaining gaps and provides actionable recommendations for reaching higher coverage targets.

### Key Statistics
- **Total Statements:** 24,575
- **Covered Statements:** 17,702
- **Missing Statements:** 6,873
- **Coverage Target:** 80-90%
- **Statements Needed for 80%:** ~1,958 more covered
- **Statements Needed for 90%:** ~4,416 more covered

---

## Priority 1: Critical Gaps (30-50% Coverage)

These modules have the lowest coverage and represent the largest opportunities for improvement.

### State API Scrapers with Low Coverage

| Module | Coverage | Missing Lines | Priority |
|--------|----------|---------------|----------|
| `texas_api.py` | 22% | 91 lines | HIGH |
| `mortgage_scraper.py` | 30% | 43 lines | HIGH |
| `pennsylvania_api.py` | 30% | 102 lines | HIGH |
| `california_api.py` | 32% | 152 lines | HIGH |
| `illinois_api.py` | 32% | 92 lines | HIGH |
| `ohio_api.py` | 33% | 81 lines | HIGH |
| `georgia_api.py` | 34% | 81 lines | HIGH |
| `newyork_api.py` | 36% | 88 lines | HIGH |
| `arizona_api.py` | 36% | 74 lines | MEDIUM |
| `northcarolina_api.py` | 39% | 68 lines | MEDIUM |
| `florida_api.py` | 40% | 78 lines | MEDIUM |
| `colorado_api.py` | 41% | 61 lines | MEDIUM |
| `newjersey_api.py` | 43% | 63 lines | MEDIUM |
| `washington_api.py` | 43% | 56 lines | MEDIUM |
| `virginia_api.py` | 47% | 55 lines | MEDIUM |

### Root Cause Analysis
Most state API scrapers have similar uncovered patterns:
1. **HTTP request methods** (lines 68-84, 98-103 typically)
2. **Search result parsing** (lines 192-224 typically)
3. **Error handling branches** (exception handlers)
4. **API authentication flows** (lines 113-129 typically)

### Recommended Approach
Create a **parameterized test template** that can be applied to all state APIs:

```python
@pytest.fixture(params=[
    ('texas_api', 'TexasAPI'),
    ('pennsylvania_api', 'PennsylvaniaAPI'),
    ('california_api', 'CaliforniaAPI'),
    # ... etc
])
def state_api_class(request):
    module_name, class_name = request.param
    module = importlib.import_module(f'datagod.scrapers.{module_name}')
    return getattr(module, class_name)
```

---

## Priority 2: Moderate Gaps (50-70% Coverage)

### State APIs at 66% Coverage
Many state APIs share the same template and have identical coverage at 66%:

| Module | Coverage | Missing |
|--------|----------|---------|
| `ak_api.py` | 66% | 79 lines |
| `al_api.py` | 66% | 79 lines |
| `ar_api.py` | 66% | 79 lines |
| `as_api.py` | 66% | 79 lines |
| `ct_api.py` | 66% | 79 lines |
| ... (25+ more) | 66% | 79 lines |

**Pattern:** All 66% coverage APIs are missing the same line ranges:
- Lines 113-129: Authentication flow
- Lines 143-148: Token refresh
- Lines 237-269: Search results parsing
- Lines 283-284, 293, 295, 297: Error paths
- Lines 329-330, 339, 341: Rate limit handling
- Lines 431-432, 446-447: Pagination
- Lines 456-458, 474-489, 494-509: Advanced features

### Other Moderate Coverage Modules

| Module | Coverage | Missing | Notes |
|--------|----------|---------|-------|
| `dc_api.py` | 59% | 105 lines | DC has unique data sources |
| `base_api_integration.py` | 67% | 72 lines | Core integration class |

---

## Priority 3: Root Level Module (db_manager.py)

**Coverage:** 81% (128 lines missing of 665)

### Missing Coverage Areas
1. **Exception handlers** in database operations
2. **Session rollback** paths
3. **Batch operation error paths**

### Key Uncovered Lines
- Lines 95-97, 110-112, 124: Exception handling
- Lines 171-173, 183-185: Session management
- Lines 606-608, 622, 629-631: Complex queries
- Lines 1401, 1406: Final cleanup

---

## Priority 4: Failing Tests (42 failures) - TEST ISOLATION ISSUE

### Root Cause Analysis

**Critical Finding:** All 42 failing tests **pass when run in isolation** but fail during the full test suite run.

```bash
# These commands produce different results:
pytest tests/test_root_main.py           # 58 passed
pytest api/src/test_api_v2.py            # 19 passed
pytest                                    # 42 failed, 7064 passed
```

**Root Cause:** Test pollution between test modules. When the full suite runs, earlier tests modify shared state (database, imports, mocks) that affects later tests.

### Affected Test Files

| File | Failures | Passes Alone |
|------|----------|--------------|
| `tests/test_root_main.py` | 34 | Yes (58/58) |
| `api/src/test_api_v2.py` | 8 | Yes (19/19) |

### Specific Issues

1. **Database State Pollution:**
   - Tests that modify the database don't properly reset state
   - SQLite connection reuse across tests causes contamination

2. **Import Cache Pollution:**
   - `main.py` module is imported by earlier tests
   - Mock patches from other tests may not be fully cleaned up

3. **Singleton Pattern Issues:**
   - `DatabaseManager` may retain state between tests
   - Global API manager instances persist

### Recommended Fixes

1. **Add pytest fixtures for database isolation:**
```python
@pytest.fixture(autouse=True)
def reset_database():
    """Reset database before each test"""
    # Setup
    yield
    # Teardown - clean up database
```

2. **Use pytest-randomly to detect order-dependent tests:**
```bash
pip install pytest-randomly
pytest --randomly-seed=12345
```

3. **Add explicit module cleanup in conftest.py:**
```python
@pytest.fixture(autouse=True)
def clean_imports():
    """Clean imported modules between tests"""
    yield
    # Remove cached imports
    sys.modules.pop('main', None)
```

4. **Use isolated database per test:**
```python
@pytest.fixture
def test_db():
    """Create isolated test database"""
    return DatabaseManager(":memory:")
```

---

## Priority 5: Near-Complete Coverage (90-99%)

These modules need minimal work to reach 100%:

| Module | Coverage | Missing | Lines |
|--------|----------|---------|-------|
| `base_scraper.py` | 99% | 1 line | 29 |
| `business_rules.py` | 99% | 1 line | 602 |
| `cross_source_validator.py` | 99% | 3 lines | 210, 280, 470 |
| `email_service.py` | 98% | 2 lines | 137-138 |
| `jurisdiction_research.py` | 98% | 2 lines | 312, 347 |
| `test_db_manager.py` | 98% | 1 line | 172 |
| `api_manager.py` | 97% | 6 lines | 36-37, 45-47, 164 |
| `generic_state_api.py` | 97% | 6 lines | 123, 266, 423-424, 464, 505 |
| `data_validation.py` | 97% | 2 lines | 55, 92 |

---

## Recommended Action Plan

### Phase 1: Quick Wins (Target: +5% coverage)
1. Fix the 42 failing tests
2. Add tests for 99% coverage modules (1-3 lines each)
3. Add error path tests for 97% modules

### Phase 2: State API Template (Target: +10% coverage)
1. Create parameterized test fixture for state APIs
2. Test common patterns across all 50 state APIs:
   - Authentication flow
   - Search functionality
   - Error handling
   - Rate limiting
   - Pagination

### Phase 3: Low Coverage Modules (Target: +8% coverage)
1. Focus on texas_api.py, pennsylvania_api.py (30% coverage)
2. Add tests for mortgage_scraper.py
3. Add tests for california_api.py, illinois_api.py

### Phase 4: Core Infrastructure (Target: +5% coverage)
1. db_manager.py exception paths
2. base_api_integration.py missing methods
3. enhanced_base_scraper.py edge cases

---

## Test Code Quality Issues

### 1. Circular Import Problems
Several modules have circular import issues requiring mock-based testing:
- `mortgage_scraper.py` - depends on neural network
- `datagod/main.py` - depends on non-existent functions in db_manager

### 2. Missing Integration Tests
The following integration scenarios are not tested:
- Full scraper orchestration workflow
- End-to-end API data flow
- Database migration rollback scenarios

### 3. Brittle Test Fixtures
Some tests rely on:
- Specific database state
- External API availability
- File system paths

---

## Coverage by Package

| Package | Coverage | Notes |
|---------|----------|-------|
| `datagod/models/` | 95-100% | Excellent coverage |
| `datagod/validation/` | 93-99% | Nearly complete |
| `datagod/services/` | 90-98% | Good coverage |
| `datagod/monitoring/` | 92% | Good coverage |
| `datagod/scrapers/categories/` | 91-99% | Good coverage |
| `datagod/scrapers/paid/` | 94-95% | Good coverage |
| `datagod/scrapers/` (states) | 22-66% | Needs work |
| `datagod/utils/` | 84-97% | Moderate coverage |
| `api/src/` | 75-85% | Moderate coverage |

---

## Conclusion

To reach **80% coverage**, focus on:
1. Fixing 42 failing tests
2. Adding parameterized tests for state API scrapers
3. Testing error paths in db_manager.py

To reach **90% coverage**, additionally:
1. Complete coverage for all state API scrapers
2. Add integration tests
3. Cover all exception handlers

**Estimated effort:**
- 80% target: 2-3 focused sessions
- 90% target: 5-7 focused sessions
