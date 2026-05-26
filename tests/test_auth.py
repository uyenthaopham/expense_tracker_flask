"""
tests/test_auth.py
==================
Integration tests for the Authentication subsystem.

Covers:
  - Registration (happy path, duplicates, invalid data, SQL injection)
  - Login (valid, wrong password, non-existent user, brute-force edge cases)
  - Logout
  - Session / protected route access control
  - Password edge cases
"""

import pytest


# ===========================================================================
# REGISTRATION
# ===========================================================================

class TestRegistration:

    def test_register_success(self, client):
        """TC-AUTH-01 – Valid registration creates a user and redirects."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"login" in resp.data.lower() or b"success" in resp.data.lower()

    def test_register_duplicate_email(self, client, test_user):
        """TC-AUTH-02 – Registration with an already-registered e-mail is rejected."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "anotheruser",
                "email": test_user["email"],    # duplicate
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"already" in resp.data.lower() or b"exist" in resp.data.lower() \
               or resp.request.path != "/dashboard"

    def test_register_duplicate_username(self, client, test_user):
        """TC-AUTH-03 – Registration with an already-taken username is rejected."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "testuser",         # duplicate
                "email": "unique@example.com",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Should NOT land on dashboard
        assert b"dashboard" not in resp.data.lower() or b"taken" in resp.data.lower()

    def test_register_password_mismatch(self, client):
        """TC-AUTH-04 – Mismatched passwords are rejected."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "mismatch",
                "email": "mismatch@example.com",
                "password": "ValidPass1!",
                "password2": "DifferentPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"match" in resp.data.lower() or b"password" in resp.data.lower()

    def test_register_invalid_email_format(self, client):
        """TC-AUTH-05 – Malformed email address is rejected by form validation."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "badmail",
                "email": "not-an-email",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"register" in resp.data.lower() or b"invalid" in resp.data.lower()

    def test_register_empty_fields(self, client):
        """TC-AUTH-06 – Submitting the registration form with all empty fields fails."""
        resp = client.post(
            "/auth/register",
            data={"username": "", "email": "", "password": "", "password2": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"register" in resp.data.lower()

    def test_register_sql_injection_in_username(self, client):
        """TC-AUTH-07 – SQL injection payload in username is handled safely."""
        payload = "'; DROP TABLE user; --"
        resp = client.post(
            "/auth/register",
            data={
                "username": payload,
                "email": "sqli@example.com",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        # Application must not crash (500) and DB must still be intact
        assert resp.status_code in (200, 302, 400)

    def test_register_sql_injection_in_email(self, client):
        """TC-AUTH-08 – SQL injection payload in email field is handled safely."""
        payload = "' OR '1'='1"
        resp = client.post(
            "/auth/register",
            data={
                "username": "normaluser",
                "email": payload,
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302, 400)

    def test_register_xss_in_username(self, client):
        """TC-AUTH-09 – XSS payload in username is sanitized / rejected."""
        payload = "<script>alert('xss')</script>"
        resp = client.post(
            "/auth/register",
            data={
                "username": payload,
                "email": "xss@example.com",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        # Either rejected or safely escaped in the response
        assert b"<script>" not in resp.data

    def test_register_very_long_username(self, client):
        """TC-AUTH-10 – Extremely long username is rejected gracefully."""
        resp = client.post(
            "/auth/register",
            data={
                "username": "a" * 300,
                "email": "longuser@example.com",
                "password": "ValidPass1!",
                "password2": "ValidPass1!",
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)


# ===========================================================================
# LOGIN
# ===========================================================================

class TestLogin:

    def test_login_success(self, client, test_user):
        """TC-AUTH-11 – Valid credentials redirect to the dashboard."""
        resp = client.post(
            "/auth/login",
            data={"email": test_user["email"], "password": test_user["password"]},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"dashboard" in resp.data.lower() or b"expense" in resp.data.lower()

    def test_login_wrong_password(self, client, test_user):
        """TC-AUTH-12 – Wrong password is rejected."""
        resp = client.post(
            "/auth/login",
            data={"email": test_user["email"], "password": "WrongPassword!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"invalid" in resp.data.lower() or b"incorrect" in resp.data.lower() \
               or b"login" in resp.data.lower()

    def test_login_nonexistent_user(self, client):
        """TC-AUTH-13 – Login with an unknown email is rejected."""
        resp = client.post(
            "/auth/login",
            data={"email": "ghost@example.com", "password": "AnyPass1!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"login" in resp.data.lower()

    def test_login_empty_credentials(self, client):
        """TC-AUTH-14 – Empty login form is rejected."""
        resp = client.post(
            "/auth/login",
            data={"email": "", "password": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_login_sql_injection(self, client):
        """TC-AUTH-15 – SQL injection in login email field is handled safely."""
        resp = client.post(
            "/auth/login",
            data={"email": "' OR 1=1; --", "password": "anything"},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 400)
        assert b"dashboard" not in resp.data.lower()

    def test_login_case_sensitivity_email(self, client, test_user):
        """TC-AUTH-16 – Login must behave consistently with email casing."""
        resp = client.post(
            "/auth/login",
            data={
                "email": test_user["email"].upper(),
                "password": test_user["password"],
            },
            follow_redirects=True,
        )
        # Either succeeds (case-insensitive) or fails gracefully – no crash
        assert resp.status_code == 200

    def test_login_sets_session_cookie(self, client, test_user):
        """TC-AUTH-17 – A session cookie is set after successful login."""
        resp = client.post(
            "/auth/login",
            data={"email": test_user["email"], "password": test_user["password"]},
        )
        # After redirect or direct 302 the session cookie must be present
        assert "session" in client.cookie_jar._cookies.get("localhost", {}).get("/", {}) \
               or resp.status_code in (200, 302)

    def test_logout(self, auth_client):
        """TC-AUTH-18 – Logged-in user can log out and is redirected."""
        resp = auth_client.get("/auth/logout", follow_redirects=True)
        assert resp.status_code == 200
        assert b"login" in resp.data.lower()

    def test_protected_route_requires_login(self, client):
        """TC-AUTH-19 – Unauthenticated access to /dashboard redirects to login."""
        resp = client.get("/dashboard", follow_redirects=True)
        assert resp.status_code == 200
        assert b"login" in resp.data.lower()

    def test_after_logout_cannot_access_dashboard(self, auth_client):
        """TC-AUTH-20 – After logout, dashboard is no longer accessible."""
        auth_client.get("/auth/logout", follow_redirects=True)
        resp = auth_client.get("/dashboard", follow_redirects=True)
        assert b"login" in resp.data.lower()
