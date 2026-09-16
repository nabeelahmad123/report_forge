"""Unit tests for the metric computation layer (spec §4.2).

Decay-fit and EEO expectations below are computed independently with plain
math in each test, not by re-deriving them from the functions under test, so
the assertions aren't tautological.
"""

import math

import numpy as np
import pandas as pd
import pytest

from app.analysis import (
    InvalidExperimentDataError,
    _compute_eeo,
    _compute_electrode_trend,
    _detect_anomalies,
    _fit_decay,
    compute_metrics,
    load_experiment_csv,
)


def _make_single_compound_run_df(k: float = 0.05, c0: float = 100.0) -> pd.DataFrame:
    t_min = np.arange(0, 91, 10)  # 0..90 step 10 -> 10 samples
    timestamps = pd.to_datetime("2026-01-01T09:00:00") + pd.to_timedelta(t_min, unit="m")
    conc = c0 * np.exp(-k * t_min)
    return pd.DataFrame(
        {
            "run_id": "TEST-RUN-1",
            "timestamp": timestamps,
            "sample_id": "TEST-001",
            "pfas_compound": "PFOA",
            "concentration_ug_l": conc,
            "current_a": 20.0,
            "voltage_v": 12.0,
            "energy_kwh": 0.01 * t_min,  # steady 0.01 kWh per minute
            "flow_rate_l_min": 5.0,
            "electrode_pair": "BDD-#1",
            "temperature_c": 22.0,
            "ph": 7.0,
        }
    )


# --- metric calculations -------------------------------------------------


def test_degradation_efficiency_and_eeo_via_compute_metrics():
    k, c0 = 0.05, 100.0
    df = _make_single_compound_run_df(k=k, c0=c0)
    result = compute_metrics(df, source="test")

    assert len(result.runs) == 1
    metrics = result.runs[0].compounds[0]

    c_end_expected = c0 * math.exp(-k * 90)
    efficiency_expected = (c0 - c_end_expected) / c0 * 100
    assert metrics.degradation_efficiency_pct == pytest.approx(efficiency_expected, rel=1e-3)

    volume_m3_expected = (5.0 * 90) / 1000  # constant 5 L/min * 90 min, to m3
    orders_expected = math.log10(c0 / c_end_expected)
    energy_expected = 0.01 * 90
    eeo_expected = energy_expected / (volume_m3_expected * orders_expected)
    assert metrics.eeo_kwh_per_m3_per_order == pytest.approx(eeo_expected, rel=1e-2)


def test_compute_eeo_matches_hand_calculation():
    # 1 kWh consumed, 100 L (0.1 m3) treated, 2 orders of magnitude removed
    # (C0=100 -> C_end=1) -> EE/O = 1 / (0.1 * 2) = 5.0
    flow_l_min = np.array([10.0, 10.0])  # constant 10 L/min over 10 min -> 100 L
    t_min = np.array([0.0, 10.0])
    eeo = _compute_eeo(energy_kwh_total=1.0, flow_l_min=flow_l_min, t_min=t_min, c0=100.0, c_end=1.0)
    assert eeo == pytest.approx(5.0, rel=1e-6)


def test_compute_eeo_returns_none_when_no_removal_occurred():
    flow_l_min = np.array([10.0, 10.0])
    t_min = np.array([0.0, 10.0])
    assert _compute_eeo(1.0, flow_l_min, t_min, c0=50.0, c_end=50.0) is None


# --- decay fitting ---------------------------------------------------------


def test_fit_decay_recovers_known_rate_constant():
    k_true, c0 = 0.08, 50.0
    t_min = np.arange(0, 61, 5)
    conc = c0 * np.exp(-k_true * t_min)

    k_fit, half_life_fit, r_squared = _fit_decay(t_min, conc)

    assert k_fit == pytest.approx(k_true, rel=1e-3)
    assert half_life_fit == pytest.approx(math.log(2) / k_true, rel=1e-3)
    assert r_squared == pytest.approx(1.0, abs=1e-4)


def test_fit_decay_returns_none_with_insufficient_points():
    k_fit, half_life_fit, r_squared = _fit_decay(np.array([0.0, 10.0]), np.array([100.0, 80.0]))
    assert (k_fit, half_life_fit, r_squared) == (None, None, None)


# --- electrode wear trend ----------------------------------------------------


def test_electrode_trend_is_stable_for_constant_rate_process():
    # Constant power, constant log-removal per window -> energy per order
    # removed should be flat across windows (see analysis.py docstring math).
    timestamps = pd.date_range("2026-01-01T09:00:00", periods=12, freq="5min")
    energy_kwh = np.linspace(0, 1.2, 12)  # constant power draw
    total_conc = 100 * np.exp(-0.05 * np.arange(12) * 5)  # constant-k decay
    df = pd.DataFrame({"timestamp": timestamps, "energy_kwh": energy_kwh, "total_conc_ug_l": total_conc})

    trend = _compute_electrode_trend(df, electrode_pair="BDD-#1")
    assert trend.trend == "stable"


def test_electrode_trend_flags_degrading_when_removal_rate_slows():
    # Same constant power, but effective removal rate decays over time
    # (fouling) -> energy per order removed should rise -> "degrading".
    timestamps = pd.date_range("2026-01-01T09:00:00", periods=12, freq="5min")
    energy_kwh = np.linspace(0, 1.2, 12)
    t_min = np.arange(12) * 5
    conc = np.empty(12)
    conc[0] = 100.0
    for i in range(1, 12):
        k_effective = 0.05 * math.exp(-0.05 * t_min[i - 1])
        conc[i] = conc[i - 1] * math.exp(-k_effective * 5)
    df = pd.DataFrame({"timestamp": timestamps, "energy_kwh": energy_kwh, "total_conc_ug_l": conc})

    trend = _compute_electrode_trend(df, electrode_pair="BDD-#3")
    assert trend.trend == "degrading"


# --- anomaly detection -------------------------------------------------------


def test_detect_anomalies_flags_ph_and_flow_but_not_clean_voltage():
    timestamps = pd.date_range("2026-01-01T09:00:00", periods=8, freq="5min")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "voltage_v": [12.0, 12.1, 11.9, 12.0, 12.2, 11.8, 12.1, 12.0],
            "ph": [7.5, 7.4, 7.3, 5.5, 5.4, 7.1, 7.0, 6.9],  # dips below PH_MIN mid-run
            "flow_rate_l_min": [7.0, 7.1, 0.1, 0.1, 7.0, 7.2, 7.0, 6.9],  # brief interruption
        }
    )
    anomalies = _detect_anomalies(df)
    types = {a.type for a in anomalies}
    assert "ph_out_of_range" in types
    assert "flow_interruption" in types
    assert "voltage_spike" not in types


def test_load_experiment_csv_rejects_missing_columns():
    bad_csv = b"run_id,timestamp\nRUN-1,2026-01-01T09:00:00\n"
    with pytest.raises(InvalidExperimentDataError, match="Missing required columns"):
        load_experiment_csv(bad_csv)
