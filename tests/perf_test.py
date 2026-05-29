import random

from locust import HttpUser, between, task


class DataGodUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login on start"""
        # Create unique user for this session
        self.username = f"perf_user_{random.randint(1000, 99999)}"
        self.password = "password123"

        # Register
        self.client.post(
            "/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@example.com",
                "password": self.password,
                "full_name": "Perf Test User",
            },
        )

        # Login
        response = self.client.post(
            "/token", data={"username": self.username, "password": self.password}
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def search_records(self):
        """Search is the most critical/frequent operation"""
        if not self.token:
            return

        queries = ["test", "mortgage", "deed", "lien", "smith"]
        query = random.choice(queries)

        with self.client.post(
            "/search",
            json={"query": query, "page": 1, "page_size": 20},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                if response.elapsed.total_seconds() > 0.2:
                    response.failure(
                        f"Latency > 200ms: {response.elapsed.total_seconds()}s"
                    )
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def view_stats(self):
        """View validation of public stats endpoint"""
        self.client.get("/stats/public")

    @task(1)
    def coverage(self):
        """Check coverage map endpoint"""
        self.client.get("/jurisdictions/coverage")
