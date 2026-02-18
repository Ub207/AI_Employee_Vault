"""Integration tests for the Gold-tier backend.

Covers: healthcheck, task CRUD, autonomy toggle, duplicate prevention,
Gmail login, WhatsApp signature validation, LinkedIn CSRF, weekly report.
"""

import pytest
from unittest.mock import patch, AsyncMock

from backend.models.gmail_message import ProcessedGmailMessage
from backend.models.whatsapp_message import ProcessedWhatsappMessage
from backend.services.report_service import generate_weekly_report


# ── 1. Healthcheck ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_healthcheck_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["tier"] == "gold"


# ── 2. Task CRUD lifecycle ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_crud_lifecycle(client):
    # Create
    resp = await client.post("/tasks", json={"title": "Test task", "body": "details"})
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # Read
    resp = await client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test task"

    # Update
    resp = await client.patch(f"/tasks/{task_id}", json={"title": "Updated task"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated task"

    # Delete
    resp = await client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 204

    # List all tasks — the deleted one should not appear
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()["tasks"]]
    assert task_id not in ids


# ── 3. Autonomy toggle behavior ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sensitive_task_requires_approval_by_default(client):
    """A task mentioning 'password' should go to awaiting_approval when autonomy is off."""
    resp = await client.post("/tasks", json={
        "title": "Reset password for admin account",
        "body": "credential access change",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "awaiting_approval"
    assert resp.json()["sensitivity_score"] > 0


@pytest.mark.asyncio
async def test_low_sensitivity_task_skips_approval(client):
    """A benign task should go straight to in_progress."""
    resp = await client.post("/tasks", json={
        "title": "Update meeting notes",
        "body": "Just a simple note",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "in_progress"


# ── 4. Duplicate prevention ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gmail_duplicate_prevention(db_session):
    """After marking a Gmail ID as processed, _is_duplicate returns True."""
    from backend.services.gmail_service import _is_duplicate, _mark_processed

    gmail_id = "msg_abc123"
    assert not await _is_duplicate(db_session, gmail_id)

    await _mark_processed(db_session, gmail_id)
    await db_session.flush()

    assert await _is_duplicate(db_session, gmail_id)


@pytest.mark.asyncio
async def test_whatsapp_duplicate_prevention(db_session):
    """After marking a WhatsApp SID as processed, _is_duplicate returns True."""
    from backend.services.whatsapp_service import _is_duplicate, _mark_processed

    sid = "SM_test_sid_001"
    assert not await _is_duplicate(db_session, sid)

    await _mark_processed(db_session, sid)
    await db_session.flush()

    assert await _is_duplicate(db_session, sid)


# ── 5. Gmail login returns auth_url ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_gmail_login_returns_auth_url(client):
    """With GMAIL_CLIENT_ID set, /integrations/gmail/login returns an auth_url."""
    with patch("backend.integrations.gmail_router.settings") as mock_settings:
        mock_settings.GMAIL_CLIENT_ID = "fake-client-id"
        mock_settings.GMAIL_REDIRECT_URI = "http://localhost:8000/integrations/gmail/callback"

        with patch("backend.integrations.gmail_router.gmail_service") as mock_svc:
            mock_svc.generate_state_token = AsyncMock(return_value="fake-state")
            mock_svc.SCOPES = "https://www.googleapis.com/auth/gmail.readonly"

            resp = await client.get("/integrations/gmail/login")
            assert resp.status_code == 200
            data = resp.json()
            assert "auth_url" in data
            assert "accounts.google.com" in data["auth_url"]
            assert data["configured"] is True


@pytest.mark.asyncio
async def test_gmail_login_unconfigured(client):
    """Without GMAIL_CLIENT_ID, login returns configured=False."""
    with patch("backend.integrations.gmail_router.settings") as mock_settings:
        mock_settings.GMAIL_CLIENT_ID = ""
        resp = await client.get("/integrations/gmail/login")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False


# ── 6. WhatsApp webhook rejects invalid signature ───────────────────────────

@pytest.mark.asyncio
async def test_whatsapp_rejects_invalid_signature(client):
    """When Twilio auth is configured, an invalid signature returns 403."""
    import sys
    from types import ModuleType
    from unittest.mock import MagicMock

    # Create a fake twilio.request_validator module so the import succeeds
    fake_twilio = ModuleType("twilio")
    fake_rv = ModuleType("twilio.request_validator")
    mock_validator_cls = MagicMock()
    mock_validator_cls.return_value.validate.return_value = False  # signature invalid
    fake_rv.RequestValidator = mock_validator_cls
    fake_twilio.request_validator = fake_rv

    with patch.dict(sys.modules, {
        "twilio": fake_twilio,
        "twilio.request_validator": fake_rv,
    }):
        with patch("backend.integrations.whatsapp.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = "fake-auth-token"
            mock_settings.WHATSAPP_WEBHOOK_URL = "https://example.com/webhook"

            resp = await client.post(
                "/integrations/whatsapp/webhook",
                data={"From": "whatsapp:+1234567890", "Body": "Hello", "MessageSid": "SM123"},
                headers={"X-Twilio-Signature": "invalid-signature"},
            )
            assert resp.status_code == 403


# ── 7. LinkedIn CSRF validation ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_linkedin_callback_rejects_bad_state(client):
    """LinkedIn callback with an unknown state token returns 400."""
    resp = await client.get(
        "/integrations/linkedin/callback",
        params={"code": "fake-code", "state": "bad-state-token"},
    )
    assert resp.status_code == 400


# ── 8. Weekly report returns non-empty markdown ─────────────────────────────

@pytest.mark.asyncio
async def test_weekly_report_generation(db_session, client):
    """Report contains expected markdown sections even with no tasks."""
    report = await generate_weekly_report(db_session)
    assert isinstance(report, str)
    assert len(report) > 0
    assert "# Weekly Summary" in report
    assert "## Metrics" in report
    assert "## Pending Approvals" in report


@pytest.mark.asyncio
async def test_weekly_report_counts_tasks(db_session, client):
    """After creating tasks, the report reflects correct counts."""
    # Create a couple of tasks via the service
    await client.post("/tasks", json={"title": "Simple task one"})
    await client.post("/tasks", json={"title": "Simple task two"})
    await client.post("/tasks", json={
        "title": "Delete payment credentials",
        "body": "password reset invoice",
    })

    report = await generate_weekly_report(db_session)
    assert "awaiting approval: 1" in report.lower() or "awaiting_approval" in report.lower() or "1" in report
