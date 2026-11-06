import pytest
from django.test import Client
from rest_framework import status


@pytest.mark.django_db
class TestAuthNegativeDefects:
    """Tests for TC-AUTH-029 and TC-AUTH-031."""

    def test_tc_auth_029_api_login_rejected_numeric_credential_values(self):
        """
        TC-AUTH-029: API login rejected - numeric credential values.
        Payload: {"email": 123, "password": 456}
        Expected: HTTP 400 or 401, no session created, no stack trace or 500 error.
        """
        client = Client()
        response = client.post(
            "/api/v1/auth/login/",
            data={"email": 123, "password": 456},
            content_type="application/json",
        )

        # Status code must be 400 Bad Request (or 401)
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ), f"Expected HTTP 400/401, got {response.status_code}"

        # No session created
        assert "_auth_user_id" not in client.session

        # Response must be JSON and not leak python stack trace
        data = response.json()
        assert "Traceback" not in str(data)
        assert "AttributeError" not in str(data)
        assert "error" in data

    def test_tc_auth_031_api_login_rejected_5000_char_email(self):
        """
        TC-AUTH-031: API login rejected - 5,000-character e-mail.
        Payload: {"email": "a"*5000, "password": "Password123!"}
        Expected: HTTP 400 or 401, no session created, no stack trace or 500 error.
        """
        client = Client()
        long_email = "a" * 5000
        response = client.post(
            "/api/v1/auth/login/",
            data={"email": long_email, "password": "Password123!"},
            content_type="application/json",
        )

        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ), f"Expected HTTP 400/401, got {response.status_code}"

        assert "_auth_user_id" not in client.session

        data = response.json()
        assert "Traceback" not in str(data)
        assert "DataError" not in str(data)
        assert "error" in data


@pytest.mark.django_db
class TestStartupAndHealthDefects:
    """Tests for TC-SUP-031."""

    def test_tc_sup_031_unknown_ui_url_returns_clean_404_page(self):
        """
        TC-SUP-031: Error handling - unknown UI URL returns a clean HTTP 404 page.
        GET /this-page-does-not-exist/
        Expected: HTTP 404 branded page, no technical debug info or URLconf leakage.
        """
        client = Client()
        response = client.get("/this-page-does-not-exist/")

        assert response.status_code == 404

        content = response.content.decode("utf-8")

        # Must display the branded 404 template
        assert "Page Not Found" in content
        assert "Back to Home" in content or "Return to Dashboard" in content

        # Must not leak technical Django debug page or URL patterns
        assert "Using the URLconf defined in" not in content
        assert "The current path," not in content
        assert "didn't match any of these" not in content
        assert "Traceback (most recent call last)" not in content


@pytest.mark.django_db
class TestLogoutDefects:
    """Tests ensuring logout links across dashboards log out users via GET and POST without 500 error."""

    def test_portal_logout_get_request_logs_out_cleanly(self):
        from apps.accounts.models import Role, User
        from apps.audit.models import AuditLog

        user = User.objects.create_user(
            email="logout_test_user@example.com",
            password="SecurePassword123!",
            first_name="Logout",
            last_name="Tester",
        )
        client = Client()
        client.force_login(user)
        assert "_auth_user_id" in client.session

        response = client.get("/logout/")
        assert response.status_code == 302
        assert response.url == "/?logged_out=1"
        assert "_auth_user_id" not in client.session
        assert response.cookies.get("ps360_just_logged_out").value == "1"

        audit_entry = AuditLog.objects.filter(
            actor=user,
            action=AuditLog.ACTION_LOGOUT,
            target_model="User",
        ).first()
        assert audit_entry is not None

    def test_portal_logout_post_request_logs_out_cleanly(self):
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="logout_post_user@example.com",
            password="SecurePassword123!",
            first_name="Post",
            last_name="Tester",
        )
        client = Client()
        client.force_login(user)
        assert "_auth_user_id" in client.session

        response = client.post("/logout/")
        assert response.status_code == 302
        assert response.url == "/?logged_out=1"
        assert "_auth_user_id" not in client.session

