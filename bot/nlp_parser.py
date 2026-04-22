"""
Natural language → structured order parser.
Handles plain-English commands like:
  "buy 0.01 BTC at market"
  "sell 1 ETH limit 3200"
  "long 0.5 BNB"
"""
from __future__ import annotations

import re
from typing import Any


_SIDE_MAP = {
    "buy": "BUY", "long": "BUY", "b": "BUY",
    "sell": "SELL", "short": "SELL", "s": "SELL",
}

_TYPE_MAP = {
    "market": "MARKET", "mkt": "MARKET", "m": "MARKET",
    "limit": "LIMIT", "lmt": "LIMIT", "l": "LIMIT",
}

_SYMBOL_RE = re.compile(r"\b([A-Z]{2,10}USDT)\b", re.IGNORECASE)
_QTY_RE = re.compile(r"\b(\d+(?:\.\d+)?)\b")
_PRICE_RE = re.compile(r"(?:at|@|price|px)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_nlp_order(text: str) -> dict[str, Any]:
    """
    Parse a natural-language order string.

    Returns a dict with keys: symbol, side, type, quantity, price (or None).
    Raises ValueError if a required field cannot be extracted.
    """
    tokens = text.lower().split()

    # --- side ---
    side: str | None = None
    for tok in tokens:
        if tok in _SIDE_MAP:
            side = _SIDE_MAP[tok]
            break
    if side is None:
        raise ValueError(
            f"Cannot determine order side from: '{text}'. "
            "Use 'buy/long' or 'sell/short'."
        )

    # --- order type ---
    order_type = "MARKET"  # default
    for tok in tokens:
        if tok in _TYPE_MAP:
            order_type = _TYPE_MAP[tok]
            break

    # --- symbol ---
    sym_match = _SYMBOL_RE.search(text)
    if sym_match:
        symbol = sym_match.group(1).upper()
    else:
        # Fallback: look for a bare coin ticker followed by USDT assumption
        coin_re = re.compile(r"\b(BTC|ETH|BNB|SOL|XRP|ADA|DOGE|AVAX|DOT|MATIC)\b", re.IGNORECASE)
        coin_match = coin_re.search(text)
        if coin_match:
            symbol = coin_match.group(1).upper() + "USDT"
        else:
            raise ValueError(
                f"Cannot extract trading symbol from: '{text}'. "
                "Include a symbol like BTCUSDT or BTC."
            )

    # --- price (explicit) ---
    price: float | None = None
    price_match = _PRICE_RE.search(text)
    if price_match:
        price = float(price_match.group(1))
        order_type = "LIMIT"

    # --- quantity ---
    # Remove the price number from consideration to avoid picking it as qty
    text_for_qty = text
    if price_match:
        text_for_qty = text[: price_match.start()] + text[price_match.end() :]
    qty_matches = _QTY_RE.findall(text_for_qty)
    if not qty_matches:
        raise ValueError(
            f"Cannot extract quantity from: '{text}'. Include a number like '0.01'."
        )
    quantity = float(qty_matches[0])

    return {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "price": price,
    }
