from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    frontend_origin: str = "http://localhost:5173"
    log_level: str = "INFO"
    demo_data_path: Path = Path(__file__).resolve().parent.parent / "data" / "demo_experiment.csv"
    regwatch_snapshot_path: Path = Path(__file__).resolve().parent.parent / "data" / "regwatch_snapshot.json"

    anthropic_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 6500
    report_rate_limit_per_minute: int = 10
    # /report is public and unauthenticated, so this bounds worst-case spend
    # from anyone hitting it directly regardless of per-IP rate limiting.
    # Tracked in-memory (resets on container restart), not persisted.
    max_llm_spend_usd: float = 5.0


settings = Settings()
