"""
Macro Data Service — Datos macroeconómicos.
Integra FRED (Federal Reserve Economic Data) y otras fuentes.

Series FRED útiles:
- GDP, UNRATE, CPIAUCSL (inflación), DFF (fed funds rate)
- T10Y2Y (yield curve), VIXCLS, DGS10 (10y treasury)
- DEXUSEU (EUR/USD), DCOILWTICO (WTI crude)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from family_office.config.settings import settings

logger = logging.getLogger(__name__)

# Key FRED series for macro monitoring
FRED_SERIES = {
    "gdp": "GDP",
    "unemployment": "UNRATE",
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "fed_funds_rate": "DFF",
    "10y_treasury": "DGS10",
    "2y_treasury": "DGS2",
    "yield_curve_10y2y": "T10Y2Y",
    "vix": "VIXCLS",
    "sp500": "SP500",
    "wti_crude": "DCOILWTICO",
    "gold": "GOLDAMGBD228NLBM",
    "eur_usd": "DEXUSEU",
    "m2_money_supply": "M2SL",
    "consumer_sentiment": "UMCSENT",
    "initial_claims": "ICSA",
    "industrial_production": "INDPRO",
    "pmi_manufacturing": "MANEMP",
    "housing_starts": "HOUST",
    "retail_sales": "RSXFS",
}

# European and Spanish macro (non-FRED)
EU_INDICATORS = {
    "ecb_rate": "ECB main refinancing rate",
    "euribor_12m": "12-month Euribor",
    "spain_gdp_growth": "Spain GDP growth rate",
    "spain_cpi": "Spain CPI",
    "spain_unemployment": "Spain unemployment rate",
    "spain_10y_bond": "Spain 10Y government bond yield",
    "ibex35": "IBEX 35 index",
}


class MacroDataService:
    """Servicio de datos macroeconómicos."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    async def get_fred_series(
        self,
        series_id: str,
        observation_start: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Obtiene datos de una serie FRED."""
        api_key = settings.market_data.fred_key
        if not api_key:
            return {"series_id": series_id, "error": "FRED API key not configured"}

        try:
            import httpx

            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }
            if observation_start:
                params["observation_start"] = observation_start

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

            observations = data.get("observations", [])
            values = []
            for obs in observations:
                if obs.get("value") != ".":
                    values.append({
                        "date": obs["date"],
                        "value": float(obs["value"]),
                    })

            result = {
                "series_id": series_id,
                "observations": values,
                "latest_value": values[0]["value"] if values else None,
                "latest_date": values[0]["date"] if values else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._cache[series_id] = result
            return result

        except Exception as e:
            logger.error(f"FRED request failed for {series_id}: {e}")
            return self._cache.get(series_id, {"series_id": series_id, "error": str(e)})

    async def get_macro_dashboard(self) -> dict[str, Any]:
        """
        Obtiene un dashboard macro completo.
        Intenta FRED primero, luego yfinance como fallback.
        """
        dashboard: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "us": {},
            "markets": {},
        }

        api_key = settings.market_data.fred_key

        if api_key:
            # Try FRED for key indicators
            key_series = ["DFF", "DGS10", "DGS2", "CPIAUCSL", "UNRATE", "T10Y2Y"]
            for series_id in key_series:
                try:
                    data = await self.get_fred_series(series_id, limit=1)
                    if data.get("latest_value") is not None:
                        name = next(
                            (k for k, v in FRED_SERIES.items() if v == series_id),
                            series_id,
                        )
                        dashboard["us"][name] = {
                            "value": data["latest_value"],
                            "date": data["latest_date"],
                        }
                except Exception as e:
                    logger.warning(f"Failed to get {series_id}: {e}")

        # Market data via yfinance (always available)
        try:
            import yfinance as yf

            market_tickers = {
                "sp500": "^GSPC",
                "nasdaq": "^IXIC",
                "euro_stoxx50": "^STOXX50E",
                "ibex35": "^IBEX",
                "vix": "^VIX",
                "gold": "GC=F",
                "wti_oil": "CL=F",
                "btc_usd": "BTC-USD",
                "eur_usd": "EURUSD=X",
            }

            for name, ticker in market_tickers.items():
                try:
                    t = yf.Ticker(ticker)
                    info = t.info
                    price = info.get("regularMarketPrice") or info.get("currentPrice")
                    change = info.get("regularMarketChangePercent")
                    dashboard["markets"][name] = {
                        "price": price,
                        "change_pct": change,
                    }
                except Exception:
                    pass

        except ImportError:
            logger.warning("yfinance not installed — market data unavailable")

        return dashboard

    async def get_economic_calendar(self) -> list[dict[str, Any]]:
        """Returns key upcoming economic events (static reference list)."""
        return [
            {"event": "FOMC Rate Decision", "frequency": "8x/year", "impact": "high"},
            {"event": "US CPI Release", "frequency": "monthly", "impact": "high"},
            {"event": "US Non-Farm Payrolls", "frequency": "monthly", "impact": "high"},
            {"event": "ECB Rate Decision", "frequency": "6x/year", "impact": "high"},
            {"event": "Spain CPI", "frequency": "monthly", "impact": "medium"},
            {"event": "US GDP (advance)", "frequency": "quarterly", "impact": "high"},
            {"event": "ISM Manufacturing PMI", "frequency": "monthly", "impact": "medium"},
            {"event": "US Initial Jobless Claims", "frequency": "weekly", "impact": "medium"},
        ]
