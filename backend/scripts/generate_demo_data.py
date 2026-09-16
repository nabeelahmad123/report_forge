"""Deterministically generates the bundled demo dataset (spec §7).

Three 90-minute runs, each tracking PFOA / PFOS / PFHxS simultaneously in a
simulated electrochemical oxidation (BDD anode) cell treating landfill
leachate, sampled every 5 minutes:

  - RUN-2026-014 "good": clean exponential decay, >=95% degradation, stable
    electrode, no anomalies.
  - RUN-2026-015 "degraded electrode": rate of removal decays as the run
    progresses (fouling), voltage drifts up with injected noise spikes
    (electrode wear signal — see app/analysis.py electrode trend detector).
  - RUN-2026-016 "interrupted flow": flow rate drops to near-zero for a
    window mid-run, concentration plateaus during that window, with a
    correlated pH dip from stagnation.

Run with: python scripts/generate_demo_data.py
Writes to: data/demo_experiment.csv (relative to backend/)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_experiment.csv"
SAMPLE_INTERVAL_MIN = 5
RUN_DURATION_MIN = 90
COMPOUNDS = {
    # (initial concentration ug/L, base first-order rate constant per minute)
    # Ordering/rates are simplified for a plausible demo, not a literature claim:
    # sulfonates (PFOS) are commonly modeled as more recalcitrant to EO than
    # PFOA; PFHxS falls in between.
    "PFOA": (110.0, 0.045),
    "PFOS": (75.0, 0.035),
    "PFHxS": (55.0, 0.040),
}


def _timestamps(start: datetime) -> list[datetime]:
    n_steps = RUN_DURATION_MIN // SAMPLE_INTERVAL_MIN + 1
    return [start + timedelta(minutes=SAMPLE_INTERVAL_MIN * i) for i in range(n_steps)]


def _process_variables_good(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    current_a = 25.0 + rng.normal(0, 0.6, n)
    voltage_v = 12.0 + rng.normal(0, 0.3, n)
    flow_l_min = 7.0 + rng.normal(0, 0.25, n)
    temperature_c = 22.0 + np.linspace(0, 1.0, n) + rng.normal(0, 0.15, n)
    ph = 7.5 - np.linspace(0, 0.9, n) + rng.normal(0, 0.05, n)
    return {
        "current_a": current_a,
        "voltage_v": voltage_v,
        "flow_l_min": flow_l_min,
        "temperature_c": temperature_c,
        "ph": ph,
    }


def _process_variables_degraded(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    current_a = 25.0 + rng.normal(0, 0.6, n)
    # Voltage climbs as electrode fouls (galvanostatic operation: constant
    # current, rising cell resistance -> rising voltage), plus noise spikes.
    voltage_v = 12.0 + np.linspace(0, 4.0, n) + rng.normal(0, 0.35, n)
    spike_idx = rng.choice(n, size=3, replace=False)
    voltage_v[spike_idx] += rng.uniform(2.5, 4.0, size=3)
    flow_l_min = 7.0 + rng.normal(0, 0.25, n)
    temperature_c = 22.0 + np.linspace(0, 1.3, n) + rng.normal(0, 0.15, n)
    ph = 7.5 - np.linspace(0, 0.9, n) + rng.normal(0, 0.05, n)
    return {
        "current_a": current_a,
        "voltage_v": voltage_v,
        "flow_l_min": flow_l_min,
        "temperature_c": temperature_c,
        "ph": ph,
    }


def _process_variables_interrupted(
    rng: np.random.Generator, n: int, interrupt_slice: slice
) -> dict[str, np.ndarray]:
    current_a = 25.0 + rng.normal(0, 0.6, n)
    voltage_v = 12.0 + rng.normal(0, 0.3, n)
    flow_l_min = 7.0 + rng.normal(0, 0.25, n)
    flow_l_min[interrupt_slice] = rng.normal(0.3, 0.1, interrupt_slice.stop - interrupt_slice.start).clip(
        min=0
    )
    temperature_c = 22.0 + np.linspace(0, 1.0, n) + rng.normal(0, 0.15, n)
    ph = 7.5 - np.linspace(0, 0.9, n) + rng.normal(0, 0.05, n)
    # Stagnation during the flow interruption pushes pH below the 6.0 floor,
    # so the anomaly detector's ph_out_of_range check has something to catch.
    ph[interrupt_slice] -= 1.4
    return {
        "current_a": current_a,
        "voltage_v": voltage_v,
        "flow_l_min": flow_l_min,
        "temperature_c": temperature_c,
        "ph": ph,
    }


def _cumulative_energy_kwh(voltage_v: np.ndarray, current_a: np.ndarray) -> np.ndarray:
    dt_hours = SAMPLE_INTERVAL_MIN / 60.0
    power_kw = voltage_v * current_a / 1000.0
    incremental = power_kw * dt_hours
    incremental[0] = 0.0
    return np.cumsum(incremental)


def _decay_concentration_constant_rate(c0: float, k: float, t_min: np.ndarray) -> np.ndarray:
    return c0 * np.exp(-k * t_min)


def _decay_concentration_with_fouling(
    c0: float, k0: float, wear_rate: float, t_min: np.ndarray
) -> np.ndarray:
    """Stepwise Euler simulation where the effective rate constant decays over
    time as the electrode fouls, producing a curve that starts as clean
    exponential decay and visibly flattens later in the run."""
    conc = np.empty_like(t_min, dtype=float)
    conc[0] = c0
    for i in range(1, len(t_min)):
        dt = t_min[i] - t_min[i - 1]
        k_effective = k0 * np.exp(-wear_rate * t_min[i - 1])
        conc[i] = conc[i - 1] * np.exp(-k_effective * dt)
    return conc


def _decay_concentration_with_plateau(
    c0: float, k: float, t_min: np.ndarray, interrupt_slice: slice
) -> np.ndarray:
    conc = np.empty_like(t_min, dtype=float)
    conc[0] = c0
    for i in range(1, len(t_min)):
        dt = t_min[i] - t_min[i - 1]
        if interrupt_slice.start <= i < interrupt_slice.stop:
            conc[i] = conc[i - 1]  # stagnant: no meaningful removal while flow is down
        else:
            conc[i] = conc[i - 1] * np.exp(-k * dt)
    return conc


def _build_run(
    run_id: str,
    sample_id: str,
    electrode_pair: str,
    start: datetime,
    process_vars: dict[str, np.ndarray],
    concentration_fn,
    rng: np.random.Generator,
) -> pd.DataFrame:
    timestamps = _timestamps(start)
    n = len(timestamps)
    t_min = np.arange(n) * SAMPLE_INTERVAL_MIN

    energy_kwh = _cumulative_energy_kwh(process_vars["voltage_v"], process_vars["current_a"])

    rows = []
    for compound, (c0, k) in COMPOUNDS.items():
        conc = concentration_fn(c0, k, t_min)
        conc = conc * (1 + rng.normal(0, 0.01, n))  # small measurement noise
        conc = np.clip(conc, 0, None)
        for i in range(n):
            rows.append(
                {
                    "run_id": run_id,
                    "timestamp": timestamps[i].isoformat(),
                    "sample_id": sample_id,
                    "pfas_compound": compound,
                    "concentration_ug_l": round(float(conc[i]), 3),
                    "current_a": round(float(process_vars["current_a"][i]), 2),
                    "voltage_v": round(float(process_vars["voltage_v"][i]), 2),
                    "energy_kwh": round(float(energy_kwh[i]), 4),
                    "flow_rate_l_min": round(float(process_vars["flow_l_min"][i]), 2),
                    "electrode_pair": electrode_pair,
                    "temperature_c": round(float(process_vars["temperature_c"][i]), 2),
                    "ph": round(float(process_vars["ph"][i]), 2),
                }
            )
    return pd.DataFrame(rows)


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = RUN_DURATION_MIN // SAMPLE_INTERVAL_MIN + 1

    good = _build_run(
        run_id="RUN-2026-014",
        sample_id="LEACHATE-B12",
        electrode_pair="BDD-#1",
        start=datetime(2026, 1, 10, 9, 0),
        process_vars=_process_variables_good(rng, n),
        concentration_fn=_decay_concentration_constant_rate,
        rng=rng,
    )

    degraded = _build_run(
        run_id="RUN-2026-015",
        sample_id="LEACHATE-C07",
        electrode_pair="BDD-#3",
        start=datetime(2026, 1, 12, 9, 0),
        process_vars=_process_variables_degraded(rng, n),
        concentration_fn=lambda c0, k, t: _decay_concentration_with_fouling(c0, k, wear_rate=0.012, t_min=t),
        rng=rng,
    )

    interrupt_slice = slice(8, 12)  # minutes 40-55
    interrupted = _build_run(
        run_id="RUN-2026-016",
        sample_id="LEACHATE-A03",
        electrode_pair="BDD-#2",
        start=datetime(2026, 1, 14, 9, 0),
        process_vars=_process_variables_interrupted(rng, n, interrupt_slice),
        concentration_fn=lambda c0, k, t: _decay_concentration_with_plateau(c0, k, t, interrupt_slice),
        rng=rng,
    )

    return pd.concat([good, degraded, interrupted], ignore_index=True)


def main() -> None:
    df = generate()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows across {df['run_id'].nunique()} runs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
