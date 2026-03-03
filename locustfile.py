"""
Locust load test for UdnNews article list API.
Target: sustain 100 QPS on GET /api/articles/
"""

from locust import HttpUser, task, constant_throughput


class ArticleListUser(HttpUser):
    # Each user issues 1 request per second; we'll launch 100 users
    # to reach ~100 RPS (QPS) on the /api/articles/ endpoint.
    wait_time = constant_throughput(1)

    @task(10)
    def list_articles(self):
        with self.client.get(
            "/api/articles/",
            headers={"Accept": "application/json"},
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(2)
    def list_articles_page2(self):
        with self.client.get(
            "/api/articles/?page=2",
            headers={"Accept": "application/json"},
            catch_response=True,
            name="/api/articles/?page=N",
        ) as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(1)
    def search_articles(self):
        with self.client.get(
            "/api/articles/?search=NBA",
            headers={"Accept": "application/json"},
            catch_response=True,
            name="/api/articles/?search=...",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status {resp.status_code}")
