"""Metric computations for electrochemical PFAS degradation experiments (spec §4.2).

All functions operate on a "long format" experiment dataframe: one row per
(run_id, timestamp, pfas_compound), with process variables (voltage, current,
energy, flow, temperature, pH, electrode_pair) replicated across the compound
rows that share a timestamp, since those variables are measured once per
sampling instant for the whole electrochemical cell.
"""

from __future__ import annotations

import io
import logging

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from app.models import (
    REQUIRED_CSV_COLUMNS,
    AnalyzeResponse,
    AnomalyFlag,
    CompoundMetrics,
    ElectrodeTrend,
    RunMetrics,
)

logger = logging.getLogger("reportforge.analysis")

# Spec §4.2 suggests "e.g. >2σ"; 3σ is used instead because a run has only
# ~19 samples, and at 2σ plain Gaussian noise trips a false spike on a clean
# run more often than not (multiple-comparisons effect, not a wear signal).
VOLTAGE_SPIKE_SIGMA = 3.0
PH_MIN, PH_MAX = 6.0, 9.0
FLOW_INTERRUPTION_FRACTION_OF_MEDIAN = 0.15
FLOW_INTERRUPTION_MIN_CONSECUTIVE = 2
ELECTRODE_TREND_WINDOWS = 3
ELECTRODE_TREND_SLOPE_THRESHOLD = 0.02


class InvalidExperimentDataError(ValueError):
    """Raised when uploaded CSV data fails schema or content validation."""


def load_experiment_csv(raw_bytes: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as exc:  # pandas raises various parser errors
        raise InvalidExperimentDataError(f"Could not parse CSV: {exc}") from exc

    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    if missing:
        raise InvalidExperimentDataError(f"Missing required columns: {', '.join(missing)}")

    if df.empty:
        raise InvalidExperimentDataError("CSV contains no data rows")

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
    except Exception as exc:
        raise InvalidExperimentDataError(f"Could not parse timestamp column: {exc}") from exc

    numeric_cols = [
        "concentration_ug_l",
        "current_a",
        "voltage_v",
        "energy_kwh",
        "flow_rate_l_min",
        "temperature_c",
        "ph",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[numeric_cols].isna().any().any():
        bad_cols = df[numeric_cols].columns[df[numeric_cols].isna().any()].tolist()
        raise InvalidExperimentDataError(
            f"Non-numeric or missing values found in columns: {', '.join(bad_cols)}"
        )

    return df.sort_values(["run_id", "pfas_compound", "timestamp"]).reset_index(drop=True)


def _exp_decay(t: np.ndarray, c0: float, k: float) -> np.ndarray:
    return c0 * np.exp(-k * t)


def _fit_decay(t_min: np.ndarray, conc: np.ndarray) -> tuple[float | None, float | None, float | None]:
    """Fit C(t) = C0 * exp(-k*t). Returns (k, half_life_min, r_squared), any of which
    may be None if the fit is not meaningful (too few points, non-decaying data)."""
    if len(t_min) < 3:
        return None, None, None
    try:
        popt, _ = curve_fit(
            _exp_decay,
            t_min,
            conc,
            p0=[max(conc[0], 1e-6), 0.01],
            bounds=(0, [np.inf, np.inf]),
            maxfev=5000,
        )
        c0_fit, k = popt
        if k <= 0:
            return None, None, None
        half_life = float(np.log(2) / k)
        predicted = _exp_decay(t_min, c0_fit, k)
        ss_res = float(np.sum((conc - predicted) ** 2))
        ss_tot = float(np.sum((conc - np.mean(conc)) ** 2))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else None
        return float(k), half_life, r_squared
    except (RuntimeError, ValueError) as exc:
        logger.warning("Decay fit failed: %s", exc)
        return None, None, None


def _compute_eeo(
    energy_kwh_total: float, flow_l_min: np.ndarray, t_min: np.ndarray, c0: float, c_end: float
) -> float | None:
    """Electrical energy per order of magnitude (EE/O), kWh/m3/order — standard
    figure of merit in electrochemical / AOP water treatment.
    EE/O = energy_kwh_total / (volume_treated_m3 * log10(C0 / C_end))
    """
    if c_end <= 0 or c0 <= c_end:
        return None
    volume_l = float(np.trapezoid(flow_l_min, t_min))
    volume_m3 = volume_l / 1000.0
    if volume_m3 <= 0:
        return None
    orders = np.log10(c0 / c_end)
    if orders <= 0:
        return None
    return float(energy_kwh_total / (volume_m3 * orders))


def _compute_electrode_trend(run_process_df: pd.DataFrame, electrode_pair: str) -> ElectrodeTrend:
    """Energy consumed per unit of total PFAS concentration removed, tracked across
    successive time windows. A rising trend signals electrode wear (spec §4.2) —
    the same drift-based degradation signature used for Li-ion capacity-fade
    analysis: more energy required over time to achieve the same removal.
    """
    df = run_process_df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    if n < ELECTRODE_TREND_WINDOWS + 1:
        return ElectrodeTrend(electrode_pair=electrode_pair, trend="insufficient_data")

    # Energy per *order of magnitude* removed (log-ratio), not per linear
    # concentration unit: for a constant-rate exponential decay under constant
    # power, this ratio is flat across time by construction (see module
    # docstring math below), so a rising trend isolates genuine electrode
    # wear (falling effective rate constant) instead of just reflecting the
    # natural flattening of any exponential decay curve.
    edges = np.linspace(0, n - 1, ELECTRODE_TREND_WINDOWS + 1).astype(int)
    ratios: list[float] = []
    for i in range(ELECTRODE_TREND_WINDOWS):
        start_idx, end_idx = edges[i], edges[i + 1]
        delta_energy = df["energy_kwh"].iloc[end_idx] - df["energy_kwh"].iloc[start_idx]
        c_start = df["total_conc_ug_l"].iloc[start_idx]
        c_end = df["total_conc_ug_l"].iloc[end_idx]
        if c_start > 0 and c_end > 0 and c_start > c_end:
            orders_removed = np.log10(c_start / c_end)
            if orders_removed > 1e-6:
                ratios.append(delta_energy / orders_removed)

    if len(ratios) < 2:
        return ElectrodeTrend(electrode_pair=electrode_pair, trend="insufficient_data")

    window_idx = np.arange(len(ratios))
    slope = float(np.polyfit(window_idx, ratios, 1)[0])
    mean_ratio = float(np.mean(ratios)) or 1e-9
    normalized_slope = slope / abs(mean_ratio)

    if normalized_slope > ELECTRODE_TREND_SLOPE_THRESHOLD:
        trend = "degrading"
    elif normalized_slope < -ELECTRODE_TREND_SLOPE_THRESHOLD:
        trend = "improving"
    else:
        trend = "stable"

    return ElectrodeTrend(
        electrode_pair=electrode_pair,
        slope_kwh_per_ug_l_removed_per_min=slope,
        trend=trend,
    )


def _detect_anomalies(run_process_df: pd.DataFrame) -> list[AnomalyFlag]:
    df = run_process_df.sort_values("timestamp").reset_index(drop=True)
    anomalies: list[AnomalyFlag] = []

    # Detrend before flagging outliers: a degrading electrode causes a real
    # upward voltage drift (rising cell resistance), which is expected
    # behavior, not a spike. Using raw mean/std would inflate the spread and
    # mask genuine transient spikes riding on top of that drift, so outliers
    # are measured against a linear trend line instead of the run mean.
    voltage = df["voltage_v"].to_numpy()
    t_idx = np.arange(len(voltage))
    trend_coeffs = np.polyfit(t_idx, voltage, 1)
    residuals = voltage - np.polyval(trend_coeffs, t_idx)
    # Robust (MAD-based) scale estimate rather than plain std: with ~19
    # samples, a couple of genuine spikes drag the ordinary std up enough to
    # mask themselves ("masking effect"). MAD is resistant to those same
    # outliers, so the threshold isn't inflated by the thing it's detecting.
    resid_mad = float(np.median(np.abs(residuals - np.median(residuals))))
    resid_std = 1.4826 * resid_mad
    if resid_std > 0:
        spike_mask = np.abs(residuals) > VOLTAGE_SPIKE_SIGMA * resid_std
        for idx in np.where(spike_mask)[0]:
            anomalies.append(
                AnomalyFlag(
                    type="voltage_spike",
                    timestamp=df["timestamp"].iloc[idx],
                    detail=f"Voltage {voltage[idx]:.2f} V deviates >{VOLTAGE_SPIKE_SIGMA}σ "
                    f"from the run's local trend ({resid_std:.2f} V residual std)",
                    severity="high",
                )
            )

    out_of_range = df[(df["ph"] < PH_MIN) | (df["ph"] > PH_MAX)]
    for _, row in out_of_range.iterrows():
        anomalies.append(
            AnomalyFlag(
                type="ph_out_of_range",
                timestamp=row["timestamp"],
                detail=f"pH {row['ph']:.2f} outside expected {PH_MIN}-{PH_MAX} range",
                severity="medium",
            )
        )

    median_flow = df["flow_rate_l_min"].median()
    if median_flow and median_flow > 0:
        is_low = df["flow_rate_l_min"] < (FLOW_INTERRUPTION_FRACTION_OF_MEDIAN * median_flow)
        run_start = None
        run_len = 0
        for i, low in enumerate([*is_low.tolist(), False]):
            if low:
                if run_start is None:
                    run_start = i
                run_len += 1
            else:
                if run_start is not None and run_len >= FLOW_INTERRUPTION_MIN_CONSECUTIVE:
                    ts = df["timestamp"].iloc[run_start]
                    anomalies.append(
                        AnomalyFlag(
                            type="flow_interruption",
                            timestamp=ts,
                            detail=f"Flow rate dropped below {FLOW_INTERRUPTION_FRACTION_OF_MEDIAN:.0%} "
                            f"of run median ({median_flow:.2f} L/min) for {run_len} consecutive samples",
                            severity="high",
                        )
                    )
                run_start, run_len = None, 0

    return sorted(anomalies, key=lambda a: a.timestamp)


def compute_metrics(df: pd.DataFrame, source: str) -> AnalyzeResponse:
    runs: list[RunMetrics] = []

    for run_id, run_df in df.groupby("run_id", sort=False):
        run_df = run_df.copy()
        electrode_pair = str(run_df["electrode_pair"].iloc[0])
        sample_id = str(run_df["sample_id"].iloc[0])
        start_time = run_df["timestamp"].min()
        end_time = run_df["timestamp"].max()
        duration_min = (end_time - start_time).total_seconds() / 60.0

        # One row per timestamp for process variables shared across compounds.
        process_df = (
            run_df.drop_duplicates(subset="timestamp")
            .loc[
                :,
                [
                    "timestamp",
                    "voltage_v",
                    "current_a",
                    "energy_kwh",
                    "flow_rate_l_min",
                    "ph",
                    "temperature_c",
                ],
            ]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        total_conc_by_ts = run_df.groupby("timestamp")["concentration_ug_l"].sum()
        process_df["total_conc_ug_l"] = process_df["timestamp"].map(total_conc_by_ts)

        compounds: list[CompoundMetrics] = []
        for compound, cdf in run_df.groupby("pfas_compound", sort=False):
            cdf = cdf.sort_values("timestamp")
            t_min = (cdf["timestamp"] - start_time).dt.total_seconds().to_numpy() / 60.0
            conc = cdf["concentration_ug_l"].to_numpy()
            c0, c_end = float(conc[0]), float(conc[-1])
            efficiency = (c0 - c_end) / c0 * 100 if c0 > 0 else 0.0

            k, half_life, r_squared = _fit_decay(t_min, conc)
            energy_total = float(process_df["energy_kwh"].iloc[-1] - process_df["energy_kwh"].iloc[0])
            process_t_min = (process_df["timestamp"] - start_time).dt.total_seconds().to_numpy() / 60.0
            eeo = _compute_eeo(
                energy_total, process_df["flow_rate_l_min"].to_numpy(), process_t_min, c0, c_end
            )

            compounds.append(
                CompoundMetrics(
                    compound=str(compound),
                    c0_ug_l=c0,
                    c_end_ug_l=c_end,
                    degradation_efficiency_pct=efficiency,
                    decay_rate_k_per_min=k,
                    half_life_min=half_life,
                    eeo_kwh_per_m3_per_order=eeo,
                    fit_r_squared=r_squared,
                    insufficient_data=k is None,
                )
            )

        electrode_trend = _compute_electrode_trend(process_df, electrode_pair)
        anomalies = _detect_anomalies(process_df)

        runs.append(
            RunMetrics(
                run_id=str(run_id),
                sample_id=sample_id,
                electrode_pair=electrode_pair,
                start_time=start_time,
                end_time=end_time,
                duration_min=duration_min,
                n_samples=len(process_df),
                compounds=compounds,
                electrode_trend=electrode_trend,
                anomalies=anomalies,
            )
        )

    return AnalyzeResponse(source=source, generated_at=pd.Timestamp.now("UTC").to_pydatetime(), runs=runs)
