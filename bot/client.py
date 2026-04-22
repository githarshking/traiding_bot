"""
Binance Futures Testnet API client wrapper.
Handles authentication, request signing, and raw HTTP calls.
Falls back to requests if python-binance client is unavailable.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("bot.client")

BASE_URL = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")


class BinanceClient:
    """Thin authenticated wrapper around the Binance Futures Testnet REST API."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})
        logger.info("BinanceClient initialised", extra={"base_url": BASE_URL})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        """Append HMAC-SHA256 signature to params dict."""
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get(self, path: str, params: dict | None = None, signed: bool = False) -> Any:
        params = params or {}
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params = self._sign(params)
        url = BASE_URL + path
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, params: dict | None = None, signed: bool = True) -> Any:
        params = params or {}
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params = self._sign(params)
        url = BASE_URL + path
        resp = self.session.post(url, params=params, timeout=10)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            logger.error(
                "HTTP error from Binance",
                extra={"status": resp.status_code, "body": resp.text},
            )
            raise
        return resp.json()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the API is reachable."""
        try:
            self._get("/fapi/v1/ping")
            return True
        except Exception as exc:
            logger.warning("Ping failed", extra={"error": str(exc)})
            return False

    def get_server_time(self) -> int:
        """Return server timestamp in ms."""
        data = self._get("/fapi/v1/time")
        return data["serverTime"]

    def get_account(self) -> dict[str, Any]:
        """Return account details (balance, positions, etc.)."""
        return self._get("/fapi/v2/account", signed=True)

    def get_balance(self) -> list[dict[str, Any]]:
        """Return list of asset balances."""
        data = self.get_account()
        return data.get("assets", [])

    def get_usdt_balance(self) -> float:
        """Return available USDT balance."""
        for asset in self.get_balance():
            if asset.get("asset") == "USDT":
                return float(asset.get("availableBalance", 0))
        return 0.0

    def get_positions(self) -> list[dict[str, Any]]:
        """Return all open positions."""
        data = self.get_account()
        return [p for p in data.get("positions", []) if float(p.get("positionAmt", 0)) != 0]

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Return open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._get("/fapi/v1/openOrders", params=params, signed=True)

    def place_order(self, params: dict[str, Any]) -> dict[str, Any]:
        """Place a futures order. params must be pre-validated."""
        logger.info("Placing order", extra={"params": params})
        result = self._post("/fapi/v1/order", params=params, signed=True)
        logger.info("Order placed", extra={"result": result})
        return result

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel a specific open order."""
        params = {"symbol": symbol, "orderId": order_id}
        params["timestamp"] = int(time.time() * 1000)
        params = self._sign(params)
        url = BASE_URL + "/fapi/v1/order"
        resp = self.session.delete(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Return 24hr ticker for a symbol."""
        return self._get("/fapi/v1/ticker/24hr", params={"symbol": symbol})

    def get_mark_price(self, symbol: str) -> float:
        """Return the current mark price for a symbol."""
        data = self._get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        return float(data.get("markPrice", 0))
