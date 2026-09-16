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


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
