from datetime import datetime
from types import SimpleNamespace

from app.models import AnalyzeResponse, AnomalyFlag, CompoundMetrics, ElectrodeTrend, RunMetrics
from app.ratelimit import InMemoryRateLimiter
from app.report import DISCLAIMER, REPORT_SECTIONS, generate_report


def _sample_metrics() -> AnalyzeResponse:
    return AnalyzeResponse(
        source="demo",
        generated_at=datetime(2026, 1, 1, 12, 0, 0),
        runs=[
            RunMetrics(
                run_id="RUN-TEST-1",
                sample_id="LEACHATE-X",
                electrode_pair="BDD-#9",
                start_time=datetime(2026, 1, 1, 9, 0, 0),
                end_time=datetime(2026, 1, 1, 10, 30, 0),
                duration_min=90.0,
                n_samples=19,
                compounds=[
                    CompoundMetrics(
                        compound="PFOA",
                        c0_ug_l=100.0,
                        c_end_ug_l=2.0,
                        degradation_efficiency_pct=98.0,
                        decay_rate_k_per_min=0.045,
                        half_life_min=15.4,
                        eeo_kwh_per_m3_per_order=400.0,
                        fit_r_squared=0.999,
                        insufficient_data=False,
                    )
                ],
                electrode_trend=ElectrodeTrend(
                    electrode_pair="BDD-#9", slope_kwh_per_ug_l_removed_per_min=0.3, trend="degrading"
                ),
                anomalies=[
                    AnomalyFlag(
                        type="voltage_spike",
                        timestamp=datetime(2026, 1, 1, 9, 30, 0),
                        detail="Voltage 19.5 V deviates from trend",
                        severity="high",
                    )
                ],
            )
        ],
    )


def test_generate_report_uses_template_fallback_when_no_api_key(monkeypatch):
    monkeypatch.setattr("app.report.settings.anthropic_api_key", None)

    result = generate_report(_sample_metrics())

    assert result.source == "template_fallback"
    assert result.model is None
    for section in REPORT_SECTIONS:
        assert f"## {section}" in result.markdown
    assert DISCLAIMER in result.markdown
    assert "RUN-TEST-1" in result.markdown


def test_generate_report_uses_llm_when_available(monkeypatch):
    monkeypatch.setattr("app.report.settings.anthropic_api_key", "fake-key")

    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="## Executive Summary\nMocked LLM report body.")]
    )

    class FakeMessages:
        def create(self, **kwargs):
            return fake_response

    class FakeAnthropicClient:
        def __init__(self, api_key=None):
            self.messages = FakeMessages()

    monkeypatch.setattr("app.report.anthropic.Anthropic", FakeAnthropicClient)

    result = generate_report(_sample_metrics())

    assert result.source == "llm"
    assert result.model == "claude-haiku-4-5"
    assert "Mocked LLM report body." in result.markdown


def test_generate_report_falls_back_when_llm_raises(monkeypatch):
    monkeypatch.setattr("app.report.settings.anthropic_api_key", "fake-key")

    class FailingMessages:
        def create(self, **kwargs):
            raise RuntimeError("simulated API outage")

    class FailingAnthropicClient:
        def __init__(self, api_key=None):
            self.messages = FailingMessages()

    monkeypatch.setattr("app.report.anthropic.Anthropic", FailingAnthropicClient)

    result = generate_report(_sample_metrics())

    assert result.source == "template_fallback"
    assert DISCLAIMER in result.markdown


def test_rate_limiter_blocks_after_max_requests():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60.0)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    # A different key has its own independent budget.
    assert limiter.allow("client-b") is True


def test_rate_limiter_recovers_after_window_elapses(monkeypatch):
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=10.0)
    current_time = [1000.0]
    monkeypatch.setattr("app.ratelimit.time.monotonic", lambda: current_time[0])

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False

    current_time[0] += 11.0
    assert limiter.allow("client-a") is True


def test_generate_report_template_handles_no_anomalies():
    metrics = _sample_metrics()
    metrics.runs[0].anomalies = []
    metrics.runs[0].electrode_trend.trend = "stable"
    result = generate_report(metrics)
    assert "No anomalies flagged." in result.markdown
