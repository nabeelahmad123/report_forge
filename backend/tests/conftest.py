import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def no_real_llm_calls_by_default(monkeypatch):
    """The test suite must never depend on (or spend money via) whatever key
    happens to be in the environment's .env — tests that want to exercise the
    LLM path explicitly monkeypatch their own fake key + client."""
    monkeypatch.setattr(settings, "anthropic_api_key", None)


@pytest.fixture(autouse=True)
def reset_llm_spend_tracker(monkeypatch):
    """The spend guard's running total is module-level state — reset it per
    test so cap behavior in one test can't leak into another."""
    monkeypatch.setattr("app.report._cumulative_spend_usd", 0.0)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
