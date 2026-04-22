"""
Input validation layer.  All validation logic lives here.
Raises ValueError with a human-readable message on failure.
"""
from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_TYPES = {"MARKET", "LIMIT"}
SYMBOL_SUFFIX = "USDT"
MIN_QUANTITY = 1e-8
MAX_QUANTITY = 1_000_000.0
MIN_PRICE = 1e-8
MAX_PRICE = 10_000_000.0


def validate_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    if not symbol.endswith(SYMBOL_SUFFIX):
        raise ValueError(f"Symbol must end with '{SYMBOL_SUFFIX}', got '{symbol}'.")
    if len(symbol) < 5 or len(symbol) > 12:
        raise ValueError(f"Symbol length must be 5-12 characters, got '{symbol}'.")
    return symbol


def validate_side(side: str) -> str:
    side = side.upper().strip()
    if side not in VALID_SIDES:
        raise ValueError(f"Side must be one of {VALID_SIDES}, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.upper().strip()
    if order_type not in VALID_TYPES:
        raise ValueError(f"Order type must be one of {VALID_TYPES}, got '{order_type}'.")
    return order_type


def validate_quantity(qty: float | str) -> float:
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a number, got '{qty}'.")
    if qty < MIN_QUANTITY:
        raise ValueError(f"Quantity too small (min {MIN_QUANTITY}), got {qty}.")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity too large (max {MAX_QUANTITY}), got {qty}.")
    return qty


def validate_price(price: float | str | None, order_type: str) -> float | None:
    if order_type == "MARKET":
        return None  # price is ignored for MARKET orders
    if price is None:
        raise ValueError("Price is required for LIMIT orders.")
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"Price must be a number, got '{price}'.")
    if price < MIN_PRICE:
        raise ValueError(f"Price too small (min {MIN_PRICE}), got {price}.")
    if price > MAX_PRICE:
        raise ValueError(f"Price too large (max {MAX_PRICE}), got {price}.")
    return price


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
) -> dict:
    """Run all validators and return a clean, normalised order dict."""
    order_type = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": order_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
    }
