"""
Shared fixtures for monitoring tests.
"""

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def sample_scraper_id():
    """Sample scraper ID"""
    return "ca_property_scraper"


@pytest.fixture
def sample_state_code():
    """Sample state code"""
    return "CA"


@pytest.fixture
def sample_metric_tags():
    """Sample metric tags"""
    return {
        "state": "CA",
        "county": "Los Angeles",
        "scraper_type": "property",
    }


@pytest.fixture
def sample_alert_rule_config():
    """Sample alert rule configuration"""
    return {
        "rule_id": "test-rule-001",
        "name": "Test Alert Rule",
        "description": "Test rule for unit testing",
        "metric_name": "test.metric",
        "threshold": 100.0,
    }
