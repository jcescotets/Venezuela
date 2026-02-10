"""
Market Data Service — Datos de mercado en tiempo real.
Integra múltiples fuentes: yfinance, Alpha Vantage, etc.

APIs y fuentes soportadas:
- yfinance: Precios, fundamentals, opciones (gratuito)
- Alpha Vantage: Precios intraday, forex, crypto (API key requerida)
- FRED: Datos macro de la Fed (API key requerida)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from family_office.config.settings import settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Servicio unificado de datos de mercado.
    Fallback entre fuentes si una no está disponible.
    """

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    # ─── Stock / ETF Data (yfinance) ──────────────────────────
    async def get_stock_data(self, ticker: str) -> dict[str, Any]:
        """Obtiene datos completos de una acción/ETF vía yfinance."""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info

            result = {
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                # Fundamentals
                "revenue": info.get("totalRevenue"),
                "ebitda": info.get("ebitda"),
                "net_income": info.get("netIncomeToCommon"),
                "free_cash_flow": info.get("freeCashflow"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                # Analyst
                "target_mean_price": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._cache[ticker] = result
            return result

        except Exception as e:
            logger.error(f"Failed to get stock data for {ticker}: {e}")
            return self._cache.get(ticker, {"ticker": ticker, "error": str(e)})

    async def get_price_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> dict[str, Any]:
        """Obtiene historial de precios."""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            return {
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "data_points": len(hist),
                "first_date": str(hist.index[0]) if len(hist) > 0 else None,
                "last_date": str(hist.index[-1]) if len(hist) > 0 else None,
                "last_close": float(hist["Close"].iloc[-1]) if len(hist) > 0 else None,
                "high": float(hist["High"].max()) if len(hist) > 0 else None,
                "low": float(hist["Low"].min()) if len(hist) > 0 else None,
                "avg_volume": float(hist["Volume"].mean()) if len(hist) > 0 else None,
                "return_pct": (
                    float((hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100)
                    if len(hist) > 1 else None
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get price history for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    # ─── Forex ────────────────────────────────────────────────
    async def get_forex_rate(self, from_currency: str, to_currency: str) -> dict[str, Any]:
        """Obtiene tipo de cambio."""
        try:
            import yfinance as yf

            pair = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(pair)
            info = ticker.info

            return {
                "pair": f"{from_currency}/{to_currency}",
                "rate": info.get("regularMarketPrice"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get forex rate {from_currency}/{to_currency}: {e}")
            return {"pair": f"{from_currency}/{to_currency}", "error": str(e)}

    # ─── Commodities / Indices ────────────────────────────────
    async def get_commodity(self, symbol: str) -> dict[str, Any]:
        """Obtiene precio de commodity/índice."""
        # Common symbols: GC=F (gold), SI=F (silver), CL=F (oil), ^SPX, ^IXIC
        return await self.get_stock_data(symbol)

    # ─── Portfolio Valuation ──────────────────────────────────
    async def get_portfolio_valuation(
        self, holdings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Valora un portfolio completo con precios actuales."""
        results = []
        total_value = 0.0

        for h in holdings:
            ticker = h.get("ticker")
            quantity = h.get("quantity", 0)

            if ticker:
                data = await self.get_stock_data(ticker)
                price = data.get("current_price", 0) or 0
                value = price * quantity
                total_value += value
                results.append({
                    **h,
                    "current_price": price,
                    "current_value": value,
                    "currency": data.get("currency", "USD"),
                })
            else:
                # Non-traded asset — use manual value
                value = h.get("current_value_usd", 0)
                total_value += value
                results.append(h)

        return {
            "total_value_usd": total_value,
            "holdings": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Alpha Vantage (premium data) ────────────────────────
    async def get_alpha_vantage_data(
        self, function: str, symbol: str, **params
    ) -> dict[str, Any]:
        """Consulta Alpha Vantage API para datos premium."""
        api_key = settings.market_data.alpha_vantage_key
        if not api_key:
            return {"error": "Alpha Vantage API key not configured"}

        try:
            import httpx

            url = "https://www.alphavantage.co/query"
            query_params = {
                "function": function,
                "symbol": symbol,
                "apikey": api_key,
                **params,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=query_params)
                return response.json()

        except Exception as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            return {"error": str(e)}
