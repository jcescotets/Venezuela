"""
Configuración central del Family Office.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.3
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )


@dataclass
class MarketDataConfig:
    alpha_vantage_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ALPHA_VANTAGE_API_KEY")
    )
    fred_key: Optional[str] = field(
        default_factory=lambda: os.getenv("FRED_API_KEY")
    )


@dataclass
class DashboardConfig:
    host: str = field(
        default_factory=lambda: os.getenv("DASHBOARD_HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "8000"))
    )
    secret_key: str = field(
        default_factory=lambda: os.getenv(
            "DASHBOARD_SECRET_KEY", "dev-secret-change-me"
        )
    )


@dataclass
class Settings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'family_office.db'}"
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    def ensure_dirs(self):
        DATA_DIR.mkdir(exist_ok=True)
        MEMORY_DIR.mkdir(exist_ok=True)


settings = Settings()
settings.ensure_dirs()
