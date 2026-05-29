"""
Load Testing for DataGod API
Using Locust for performance testing

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Web UI available at: http://localhost:8089
"""

import json
import logging
import random

from locust import HttpUser, between, events, task

logger = logging.getLogger(__name__)


class DataGodUser(HttpUser):
    """Simulates a typical DataGod user accessing the API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts. Perform login."""
        self.token = None
        self.login()

    def login(self):
        """Authenticate and get JWT token."""
        response = self.client.post(
            "/api/v2/token",
            data={
                "username": "demo@example.com",
                "password": "demopassword123",
                "grant_type": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            logger.info("Login successful")
        else:
            logger.warning(f"Login failed: {response.status_code}")

    @property
    def auth_headers(self):
        """Get authorization headers."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def get_health(self):
        """Check API health endpoint - high frequency."""
        self.client.get("/api/v2/health")

    @task(3)
    def get_records(self):
        """Fetch records with pagination."""
        page = random.randint(1, 10)
        limit = random.choice([10, 25, 50])

        self.client.get(
            f"/api/v2/records?page={page}&limit={limit}", headers=self.auth_headers
        )

    @task(4)
    def search_records(self):
        """Search for records with various queries."""
        queries = [
            "property",
            "mortgage",
            "deed",
            "lien",
            "foreclosure",
            "Harris County",
            "Los Angeles",
            "New York",
        ]
        query = random.choice(queries)

        self.client.get(f"/api/v2/search?q={query}&limit=20", headers=self.auth_headers)

    @task(2)
    def get_jurisdictions(self):
        """Fetch jurisdictions list."""
        self.client.get("/api/v2/jurisdictions?limit=50", headers=self.auth_headers)

    @task(1)
    def get_dashboard_stats(self):
        """Fetch dashboard statistics."""
        self.client.get("/api/v2/stats", headers=self.auth_headers)

    @task(1)
    def get_user_profile(self):
        """Fetch current user profile."""
        if self.token:
            self.client.get("/api/v2/users/me", headers=self.auth_headers)


class AnonymousUser(HttpUser):
    """Simulates unauthenticated users accessing public endpoints."""

    wait_time = between(2, 5)

    @task(3)
    def get_health(self):
        """Check API health."""
        self.client.get("/api/v2/health")

    @task(2)
    def view_public_records(self):
        """View public records (if enabled)."""
        self.client.get("/api/v2/records?limit=10")

    @task(1)
    def attempt_login(self):
        """Simulate login attempts."""
        self.client.post(
            "/api/v2/token",
            data={
                "username": f"user{random.randint(1, 1000)}@example.com",
                "password": "testpassword",
                "grant_type": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


class AdminUser(HttpUser):
    """Simulates admin users performing management tasks."""

    wait_time = between(3, 8)
    weight = 1  # Less frequent than regular users

    def on_start(self):
        """Login as admin."""
        self.token = None
        response = self.client.post(
            "/api/v2/token",
            data={
                "username": "admin@example.com",
                "password": "adminpassword123",
                "grant_type": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(2)
    def list_users(self):
        """List all users (admin only)."""
        self.client.get("/api/v2/users", headers=self.auth_headers)

    @task(1)
    def get_system_stats(self):
        """Get system statistics."""
        self.client.get("/api/v2/stats", headers=self.auth_headers)


# Event hooks for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request metrics."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    elif response_time > 1000:  # Slow requests (>1s)
        logger.warning(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test completed."""
    logger.info("Load test completed.")

    # Print summary
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
