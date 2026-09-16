from datetime import datetime

from pydantic import BaseModel, Field

REQUIRED_CSV_COLUMNS = [
    "run_id",
    "timestamp",
    "sample_id",
    "pfas_compound",
    "concentration_ug_l",
    "current_a",
    "voltage_v",
    "energy_kwh",
    "flow_rate_l_min",
    "electrode_pair",
    "temperature_c",
    "ph",
]


class CompoundMetrics(BaseModel):
    compound: str
    c0_ug_l: float = Field(..., description="Starting concentration, micrograms/L")
    c_end_ug_l: float = Field(..., description="Final measured concentration, micrograms/L")
    degradation_efficiency_pct: float
    decay_rate_k_per_min: float | None = Field(
        None, description="Fitted first-order rate constant k in C(t) = C0 * exp(-k*t)"
    )
    half_life_min: float | None = None
    eeo_kwh_per_m3_per_order: float | None = Field(
        None, description="Electrical energy per order of magnitude removed"
    )
    fit_r_squared: float | None = None
    insufficient_data: bool = False


class AnomalyFlag(BaseModel):
    type: str
    timestamp: datetime
    detail: str
    severity: str = "medium"


class ElectrodeTrend(BaseModel):
    electrode_pair: str
    slope_kwh_per_ug_l_removed_per_min: float | None = None
    trend: str = Field(..., description="'stable' | 'degrading' | 'improving' | 'insufficient_data'")


class RunMetrics(BaseModel):
    run_id: str
    sample_id: str
    electrode_pair: str
    start_time: datetime
    end_time: datetime
    duration_min: float
    n_samples: int
    compounds: list[CompoundMetrics]
    electrode_trend: ElectrodeTrend
    anomalies: list[AnomalyFlag]


class AnalyzeResponse(BaseModel):
    source: str = Field(..., description="'upload' or 'demo'")
    generated_at: datetime
    runs: list[RunMetrics]


class ReportResponse(BaseModel):
    markdown: str
    source: str = Field(..., description="'llm' or 'template_fallback'")
    model: str | None = None
    generated_at: datetime


class RegWatchItem(BaseModel):
    title: str
    source: str
    published_at: datetime
    url: str
    summary: str
    category: str = Field(..., description="'Regulation' | 'Litigation' | 'Science' | 'Industry'")
    relevance_score: int = Field(..., ge=1, le=5)


class FeedResponse(BaseModel):
    source: str = Field(..., description="'snapshot' or 'live'")
    generated_at: datetime
    items: list[RegWatchItem]
