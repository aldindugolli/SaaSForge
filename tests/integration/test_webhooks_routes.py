"""Integration tests for customer webhook management routes."""

import uuid


class TestWebhookRoutes:
    def test_webhook_page_requires_login(self, client):
        response = client.get("/webhooks/")
        assert response.status_code == 302

    def test_webhook_create_requires_auth(self, client):
        response = client.post("/webhooks/create", data={
            "url": "https://example.com/hook",
            "events": ["subscription.updated"],
        })
        assert response.status_code == 302

    def test_webhook_create_login_redirect(self, client):
        response = client.post("/webhooks/create", data={
            "url": "https://example.com/hook",
            "events": ["subscription.updated"],
        })
        assert "/auth/login" in response.headers.get("Location", "")

    def test_webhook_delete_requires_login(self, client):
        response = client.post(f"/webhooks/{uuid.uuid4()}/delete")
        assert response.status_code == 302

    def test_webhook_delivery_history_requires_login(self, client):
        response = client.get(f"/webhooks/{uuid.uuid4()}/deliveries")
        assert response.status_code == 302

    def test_webhook_toggle_requires_login(self, client):
        response = client.post(f"/webhooks/{uuid.uuid4()}/toggle")
        assert response.status_code == 302

    def test_webhook_test_requires_login(self, client):
        response = client.post(f"/webhooks/{uuid.uuid4()}/test")
        assert response.status_code == 302

    def test_webhook_retry_requires_login(self, client):
        response = client.post(f"/webhooks/deliveries/{uuid.uuid4()}/retry")
        assert response.status_code == 302
