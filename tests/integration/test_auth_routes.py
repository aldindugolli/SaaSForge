"""Integration tests for auth routes."""
import pytest


class TestAuthRoutes:
    def test_login_page(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Sign In" in response.data or b"Welcome" in response.data

    def test_register_page(self, client):
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert b"Create" in response.data

    def test_register_submission(self, client):
        response = client.post("/auth/register", data={
            "email": "integration@example.com",
            "password": "Integration123!",
            "name": "Integration Test",
        })
        assert response.status_code in (200, 302)

    def test_login_submission(self, client, registered_user):
        response = client.post("/auth/login", data={
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        assert response.status_code in (200, 302)

    def test_login_invalid(self, client):
        response = client.post("/auth/login", data={
            "email": "wrong@example.com",
            "password": "WrongPass123!",
        })
        assert response.status_code == 200
        assert b"Invalid" in response.data

    def test_forgot_password_page(self, client):
        response = client.get("/auth/forgot-password")
        assert response.status_code == 200
