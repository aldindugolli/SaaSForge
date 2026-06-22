"""Integration tests for admin routes."""


class TestAdminRoutes:
    def test_admin_page_requires_login(self, client):
        response = client.get("/admin/")
        assert response.status_code == 302

    def test_admin_page_requires_authentication(self, client):
        response = client.get("/admin/")
        assert "/auth/login" in response.headers.get("Location", "")

    def test_admin_performance_page_requires_login(self, client):
        response = client.get("/admin/performance")
        assert response.status_code == 302

    def test_admin_business_metrics_requires_login(self, client):
        response = client.get("/admin/business-metrics")
        assert response.status_code == 302

    def test_admin_webhooks_requires_login(self, client):
        response = client.get("/admin/webhooks")
        assert response.status_code == 302

    def test_admin_api_stats_requires_login(self, client):
        response = client.get("/admin/api-stats")
        assert response.status_code == 302

    def test_admin_users_requires_login(self, client):
        response = client.get("/admin/users")
        assert response.status_code == 302

    def test_admin_subscriptions_requires_login(self, client):
        response = client.get("/admin/subscriptions")
        assert response.status_code == 302

    def test_admin_payments_requires_login(self, client):
        response = client.get("/admin/payments")
        assert response.status_code == 302

    def test_admin_audit_logs_requires_login(self, client):
        response = client.get("/admin/audit-logs")
        assert response.status_code == 302

    def test_admin_cache_requires_login(self, client):
        response = client.get("/admin/cache")
        assert response.status_code == 302

    def test_admin_jobs_requires_login(self, client):
        response = client.get("/admin/jobs")
        assert response.status_code == 302

    def test_admin_analytics_requires_login(self, client):
        response = client.get("/admin/analytics")
        assert response.status_code == 302

    def test_admin_trial_analytics_requires_login(self, client):
        response = client.get("/admin/trial-analytics")
        assert response.status_code == 302

    def test_admin_reset_demo_requires_login(self, client):
        response = client.post("/admin/reset-demo")
        assert response.status_code == 302
