# DataGod Load Testing

Load testing suite using [Locust](https://locust.io/) for stress testing the DataGod API.

## Installation

```bash
pip install locust
```

## Running Load Tests

### Interactive Mode (Web UI)

Start Locust with web interface:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser to:
- Set number of users
- Set spawn rate
- Start/stop tests
- View real-time statistics

### Headless Mode (CLI)

Run without web interface (for CI/CD):

```bash
# Basic test: 100 users, 10 users/sec spawn rate, 5 minutes
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless

# Export results to CSV
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --csv=results/load_test
```

## Test Scenarios

### DataGodUser
Simulates typical user behavior:
- Login and get JWT token
- Browse dashboard/stats
- Perform searches
- View record details
- Export data

### AuthenticationUser
Focuses on authentication stress testing:
- Valid login attempts
- Invalid login attempts (testing error handling)
- Get current user info

### RegistrationUser
Tests registration rate limiting:
- New user registration attempts
- Validates rate limiting under load

### HeavySearchUser
Simulates power users:
- Complex multi-parameter searches
- Rapid sequential searches
- Bulk data exports

## Running Specific User Classes

Test only specific scenarios:

```bash
# Only authentication tests
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    AuthenticationUser

# Multiple specific classes
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    DataGodUser AuthenticationUser
```

## Performance Targets

Based on production requirements:

| Metric | Target | Critical |
|--------|--------|----------|
| Avg Response Time | < 200ms | < 500ms |
| 95th Percentile | < 500ms | < 1000ms |
| Error Rate | < 1% | < 5% |
| Concurrent Users | 100 | 50 |
| Requests/sec | 100+ | 50+ |

## Distributed Testing

For larger scale tests across multiple machines:

**Master:**
```bash
locust -f tests/load/locustfile.py --master
```

**Workers:**
```bash
locust -f tests/load/locustfile.py --worker --master-host=<master-ip>
```

## Results Analysis

After running tests, check:
1. Response time distribution
2. Error rate by endpoint
3. Requests per second over time
4. Resource utilization (CPU, memory, DB connections)

## Troubleshooting

### High Error Rate
- Check if API server is running
- Verify demo user exists in database
- Check rate limiting configuration

### Slow Response Times
- Monitor database query performance
- Check Redis cache hit rate
- Review API server logs

### Connection Errors
- Increase server worker count
- Check network/firewall settings
- Monitor open file descriptor limits
