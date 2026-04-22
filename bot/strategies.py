"""
Strategy preset loader.
Reads strategies.yaml and executes a named strategy
through the standard order placement pipeline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bot.logging_config import get_logger
from bot.validators import validate_order

logger = get_logger("bot.strategies")

_YAML_PATH = Path(__file__).parent.parent / "strategies.yaml"


def load_strategies() -> dict[str, Any]:
    """Load all strategy definitions from strategies.yaml."""
    if not _YAML_PATH.exists():
        raise FileNotFoundError(f"strategies.yaml not found at {_YAML_PATH}")
    with open(_YAML_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("strategies", {})


def get_strategy(name: str) -> dict[str, Any]:
    """Return a single strategy by key, raising KeyError if not found."""
    strategies = load_strategies()
    if name not in strategies:
        available = ", ".join(strategies.keys())
        raise KeyError(
            f"Strategy '{name}' not found. Available: {available}"
        )
    raw = strategies[name]
    return validate_order(
        symbol=raw["symbol"],
        side=raw["side"],
        order_type=raw["type"],
        quantity=raw["quantity"],
        price=raw.get("price"),
    )


def list_strategies() -> list[dict[str, Any]]:
    """Return a list of strategy summary dicts for display."""
    strategies = load_strategies()
    result = []
    for key, s in strategies.items():
        result.append(
            {
                "key": key,
                "name": s.get("name", key),
                "symbol": s.get("symbol", ""),
                "side": s.get("side", ""),
                "type": s.get("type", ""),
                "quantity": s.get("quantity", ""),
                "price": s.get("price", "MARKET"),
                "description": s.get("description", ""),
            }
        )
    return result
