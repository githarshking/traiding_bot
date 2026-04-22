"""
Order formatting and placement logic.
Converts a validated order dict into a Binance API params dict
and executes it (or simulates it in dry-run mode).
"""
from __future__ import annotations

import os
import time
from typing import Any

from bot.client import BinanceClient
from bot.logging_config import get_logger

logger = get_logger("bot.orders")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def build_order_params(order: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a validated order dict to Binance API request params.

    Input shape:
        {"symbol": str, "side": str, "type": str, "quantity": float, "price": float | None}

    Output: Binance-compatible params dict.
    """
    params: dict[str, Any] = {
        "symbol": order["symbol"],
        "side": order["side"],
        "type": order["type"],
        "quantity": order["quantity"],
        "positionSide": "BOTH",  # default one-way mode
    }
    if order["type"] == "LIMIT":
        if order.get("price") is None:
            raise ValueError("LIMIT order requires a price.")
        params["price"] = order["price"]
        params["timeInForce"] = "GTC"  # Good Till Cancelled
    return params


def simulate_order(params: dict[str, Any]) -> dict[str, Any]:
    """
    Return a fake Binance response for dry-run mode.
    Mirrors the shape of a real /fapi/v1/order response.
    """
    fake_id = int(time.time() * 1000) % 10_000_000
    avg_price = params.get("price", 0.0) or 30000.0  # fallback for MARKET
    return {
        "orderId": fake_id,
        "symbol": params["symbol"],
        "status": "FILLED (DRY-RUN)",
        "clientOrderId": f"dryrun_{fake_id}",
        "price": str(params.get("price", "0.00000000")),
        "avgPrice": str(avg_price),
        "origQty": str(params["quantity"]),
        "executedQty": str(params["quantity"]),
        "type": params["type"],
        "side": params["side"],
        "timeInForce": params.get("timeInForce", "N/A"),
        "updateTime": int(time.time() * 1000),
    }


def place_order(
    client: BinanceClient | None,
    order: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Build params and execute (or simulate) an order.

    Args:
        client: Authenticated BinanceClient.
        order: Validated order dict from validators.validate_order().
        dry_run: If True, skip real API call and return simulated result.

    Returns:
        Binance order response dict.
    """
    params = build_order_params(order)
    effective_dry_run = dry_run or DRY_RUN

    if effective_dry_run:
        logger.info("Dry-run order simulated", extra={"params": params})
        return simulate_order(params)

    return client.place_order(params)
