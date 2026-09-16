"""LLM lab report generation (spec §4.3) with a deterministic template fallback.

Never lets a report request crash or hang on the LLM: any failure (missing
key, API error, timeout) falls back to a template report built directly from
the metrics, per spec §10's "graceful LLM failure handling" requirement.
"""

from __future__ import annotations

import json
import logging
import threading

import anthropic

from app.config import settings
from app.models import AnalyzeResponse, ReportResponse

logger = logging.getLogger("reportforge.report")

# claude-haiku-4-5 pricing ($/1M tokens) — used only for the spend guard's
# rough running estimate below, not billing-accurate if LLM_MODEL is changed.
_HAIKU_INPUT_USD_PER_MTOK = 1.00
_HAIKU_OUTPUT_USD_PER_MTOK = 5.00

_spend_lock = threading.Lock()
_cumulative_spend_usd = 0.0


def _spend_cap_reached() -> bool:
    with _spend_lock:
        return _cumulative_spend_usd >= settings.max_llm_spend_usd


def _record_spend(input_tokens: int, output_tokens: int) -> None:
    global _cumulative_spend_usd
    cost = (input_tokens / 1_000_000) * _HAIKU_INPUT_USD_PER_MTOK
    cost += (output_tokens / 1_000_000) * _HAIKU_OUTPUT_USD_PER_MTOK
    with _spend_lock:
        _cumulative_spend_usd += cost
        total = _cumulative_spend_usd
    logger.info(
        "LLM call cost ~$%.4f, cumulative ~$%.2f / $%.2f cap", cost, total, settings.max_llm_spend_usd
    )


REPORT_SECTIONS = [
    "Executive Summary",
    "Degradation Performance",
    "Energy Analysis",
    "Electrode Health",
    "Anomalies & Data Quality",
    "Recommendations",
    "Appendix",
]

# Hardcoded, not LLM-recalled (see pfasuiki-demo-spec.md §4.3). These are NOT
# claimed literature citations — published EE/O figures for PFAS EO vary hugely
# by matrix, current density and treatment scale, and pinning a specific number
# without a verified source would just be a different flavor of hallucination.
# Instead, this range is derived from this bench-scale flow-through configuration
# itself (~10-30 A, <20 V, single-digit L/min), so the LLM has a fixed, internally
# consistent anchor to call a given run "typical" or "elevated" against — not an
# external authority.
REFERENCE_BENCHMARKS = {
    "degradation_efficiency_pct_typical_range": [70, 99],
    "eeo_kwh_per_m3_per_order_typical_range": [0.3, 2.0],
    "half_life_min_typical_range": [10, 90],
    "note": (
        "Approximate reference ranges for THIS bench-scale flow-through EO configuration "
        "(order 10-30 A, sub-20 V, L/min-scale flow) — not a literature citation. Real-world "
        "reported EE/O values for PFAS electrochemical oxidation vary far more widely by water "
        "matrix, current density, and treatment scale. Use this range only to call out whether a "
        "given run is typical or elevated relative to the other runs in this dataset."
    ),
}

SYSTEM_PROMPT = (
    "You are a senior electrochemical water treatment engineer writing internal lab reports "
    "for PFAS degradation experiments. Be precise, quantitative, and honest about uncertainty. "
    "Never invent numbers — only use metrics and benchmark values provided in the JSON payload. "
    "Do not cite benchmark figures from memory. If a metric needed for a section is missing or "
    "null, say 'insufficient data' for that point rather than guessing."
)


def _build_user_prompt(metrics: AnalyzeResponse) -> str:
    payload = {
        "experiment_metrics": metrics.model_dump(mode="json"),
        "reference_benchmarks": REFERENCE_BENCHMARKS,
    }
    sections = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(REPORT_SECTIONS))
    return (
        "Write a structured Markdown lab report from the experiment metrics JSON below. "
        f"Use exactly these top-level sections, in this order, as '## ' Markdown headings:\n{sections}\n\n"
        "Executive Summary: 3-4 sentences — what was tested, headline result, key concern.\n"
        "Degradation Performance: per-compound efficiency, half-life, comparison to the provided "
        "reference_benchmarks ranges (caveat that these are approximate reference ranges, not a "
        "specific study).\n"
        "Energy Analysis: EEO values per compound, a brief cost-implication note.\n"
        "Electrode Health: interpret the electrode_trend field per run — explain what a "
        "'degrading' trend means physically (rising energy cost per order of magnitude removed, "
        "consistent with electrode fouling/wear).\n"
        "Anomalies & Data Quality: list flagged anomalies with timestamps and what they mean.\n"
        "Recommendations: 3-5 concrete, specific next steps referencing actual run_ids/electrode_pairs "
        "from the data.\n"
        "Appendix: a compact Markdown table of the key metrics per run/compound.\n\n"
        f"Experiment metrics and reference benchmarks (JSON):\n```json\n{json.dumps(payload, indent=2)}\n```"
    )


def _call_llm(metrics: AnalyzeResponse) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(metrics)}],
    )
    text_blocks = [block.text for block in response.content if block.type == "text"]
    _record_spend(response.usage.input_tokens, response.usage.output_tokens)
    return "\n".join(text_blocks).strip()


def _format_compound_line(c) -> str:
    eff = f"{c.degradation_efficiency_pct:.1f}%"
    half_life = f"{c.half_life_min:.1f} min" if c.half_life_min is not None else "insufficient data"
    eeo = (
        f"{c.eeo_kwh_per_m3_per_order:.1f} kWh/m³/order"
        if c.eeo_kwh_per_m3_per_order is not None
        else "insufficient data"
    )
    return (
        f"- **{c.compound}**: {c.c0_ug_l:.1f} → {c.c_end_ug_l:.2f} µg/L ({eff} removed), "
        f"half-life {half_life}, EEO {eeo}"
    )


def _template_report(metrics: AnalyzeResponse) -> str:
    """Deterministic, LLM-free report built straight from the metrics JSON.
    Used whenever the LLM is unavailable or fails — never blocks the demo."""
    lines: list[str] = ["# Lab Report (template fallback — AI unavailable)", ""]

    lines += ["## Executive Summary", ""]
    for run in metrics.runs:
        best = max(run.compounds, key=lambda c: c.degradation_efficiency_pct, default=None)
        if best:
            lines.append(
                f"- {run.run_id} ({run.sample_id}, {run.electrode_pair}): best result "
                f"{best.compound} at {best.degradation_efficiency_pct:.1f}% degradation over "
                f"{run.duration_min:.0f} min; electrode trend **{run.electrode_trend.trend}**; "
                f"{len(run.anomalies)} anomaly event(s) flagged."
            )
    lines.append("")

    lines += ["## Degradation Performance", ""]
    for run in metrics.runs:
        lines.append(f"**{run.run_id}**")
        for c in run.compounds:
            lines.append(_format_compound_line(c))
        lines.append("")

    lines += ["## Energy Analysis", ""]
    for run in metrics.runs:
        lines.append(f"**{run.run_id}** EEO by compound:")
        for c in run.compounds:
            eeo = (
                f"{c.eeo_kwh_per_m3_per_order:.1f} kWh/m³/order"
                if c.eeo_kwh_per_m3_per_order is not None
                else "insufficient data"
            )
            lines.append(f"- {c.compound}: {eeo}")
        lines.append("")

    lines += ["## Electrode Health", ""]
    for run in metrics.runs:
        t = run.electrode_trend
        lines.append(
            f"- {run.run_id} ({t.electrode_pair}): **{t.trend}** "
            f"(slope {t.slope_kwh_per_ug_l_removed_per_min:.4f} kWh per order removed per window)"
            if t.slope_kwh_per_ug_l_removed_per_min is not None
            else f"- {run.run_id} ({t.electrode_pair}): {t.trend}"
        )
    lines.append("")

    lines += ["## Anomalies & Data Quality", ""]
    any_anomaly = False
    for run in metrics.runs:
        for a in run.anomalies:
            any_anomaly = True
            lines.append(f"- [{run.run_id}] {a.timestamp.isoformat()} — **{a.type}**: {a.detail}")
    if not any_anomaly:
        lines.append("- No anomalies flagged.")
    lines.append("")

    lines += ["## Recommendations", ""]
    for run in metrics.runs:
        if run.electrode_trend.trend == "degrading":
            lines.append(
                f"- {run.run_id}: electrode {run.electrode_trend.electrode_pair} shows a degrading "
                "efficiency trend — inspect for fouling before the next cycle."
            )
        flow_events = [a for a in run.anomalies if a.type == "flow_interruption"]
        if flow_events:
            lines.append(
                f"- {run.run_id}: investigate flow system reliability "
                f"({len(flow_events)} interruption(s) detected)."
            )
    if not any(run.electrode_trend.trend == "degrading" or run.anomalies for run in metrics.runs):
        lines.append("- No corrective actions indicated by this dataset.")
    lines.append("")

    lines += ["## Appendix", ""]
    lines.append(
        "| Run | Compound | C0 (µg/L) | C_end (µg/L) | Efficiency | Half-life (min) | EEO (kWh/m³/order) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for run in metrics.runs:
        for c in run.compounds:
            half_life = f"{c.half_life_min:.1f}" if c.half_life_min is not None else "n/a"
            eeo = f"{c.eeo_kwh_per_m3_per_order:.1f}" if c.eeo_kwh_per_m3_per_order is not None else "n/a"
            lines.append(
                f"| {run.run_id} | {c.compound} | {c.c0_ug_l:.1f} | {c.c_end_ug_l:.2f} | "
                f"{c.degradation_efficiency_pct:.1f}% | {half_life} | {eeo} |"
            )

    return "\n".join(lines)


def generate_report(metrics: AnalyzeResponse) -> ReportResponse:
    import pandas as pd  # local import: only needed for the timestamp helper below

    generated_at = pd.Timestamp.now("UTC").to_pydatetime()

    if not settings.anthropic_api_key:
        logger.info("No ANTHROPIC_API_KEY configured — using template fallback report")
        return ReportResponse(
            markdown=_template_report(metrics),
            source="template_fallback",
            model=None,
            generated_at=generated_at,
        )

    if _spend_cap_reached():
        logger.warning(
            "LLM spend cap ($%.2f) reached — using template fallback report", settings.max_llm_spend_usd
        )
        return ReportResponse(
            markdown=_template_report(metrics),
            source="template_fallback",
            model=None,
            generated_at=generated_at,
        )

    try:
        markdown = _call_llm(metrics)
        if not markdown:
            raise ValueError("LLM returned empty response")
        return ReportResponse(
            markdown=markdown, source="llm", model=settings.llm_model, generated_at=generated_at
        )
    except Exception as exc:  # noqa: BLE001 - any LLM failure must fall back, never crash
        logger.warning("LLM report generation failed, using template fallback: %s", exc)
        return ReportResponse(
            markdown=_template_report(metrics),
            source="template_fallback",
            model=None,
            generated_at=generated_at,
        )
