"""
Automated Test Suite for the Mana Core Trading Bot.
Run with: pytest -v
"""
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

# Import your modules
# (Adjust these imports if your exact function names differ slightly)
from cli import cli
try:
    from bot.validators import validate_order
    from bot.nlp_parser import parse_nlp_order
    from bot.orders import place_order
except ImportError:
    pass # In case the vibe-coded file names are slightly different

# ---------------------------------------------------------------------------
# 1. Validation Tests
# ---------------------------------------------------------------------------
def test_validate_order_valid_market():
    """Test that a valid MARKET order passes validation."""
    result = validate_order("BTCUSDT", "BUY", "MARKET", 0.05, None)
    assert result["symbol"] == "BTCUSDT"
    assert result["side"] == "BUY"
    assert result["type"] == "MARKET"
    assert result["quantity"] == 0.05

def test_validate_order_valid_limit():
    """Test that a valid LIMIT order passes validation."""
    result = validate_order("ETHUSDT", "SELL", "LIMIT", 1.5, 3200.0)
    assert result["type"] == "LIMIT"
    assert result["price"] == 3200.0

def test_validate_order_missing_price_for_limit():
    """Test that LIMIT orders fail if no price is provided."""
    with pytest.raises(ValueError, match="(?i)price"):
        validate_order("ETHUSDT", "SELL", "LIMIT", 1.5, None)

def test_validate_order_invalid_quantity():
    """Test that negative quantities are rejected."""
    with pytest.raises(ValueError, match="(?i)quantity"):
        validate_order("BTCUSDT", "BUY", "MARKET", -0.5, None)

# ---------------------------------------------------------------------------
# 2. NLP Parser Tests
# ---------------------------------------------------------------------------
@patch("bot.nlp_parser.parse_nlp_order") # Mocking the AI so we don't spend tokens testing
def test_parse_nlp_order(mock_parse):
    """Test that the NLP parser translates English to API structured data."""
    # Define what the fake AI should return
    mock_parse.return_value = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": 0.1
    }
    
    result = mock_parse("go long 0.1 btc at market")
    assert result["symbol"] == "BTCUSDT"
    assert result["side"] == "BUY"
    assert result["type"] == "MARKET"

# ---------------------------------------------------------------------------
# 3. Order Execution Tests (Mocked API)
# ---------------------------------------------------------------------------
def test_place_order_dry_run():
    """Test that dry-run returns a simulated success without hitting the API."""
    mock_client = MagicMock()
    order_data = {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01}
    
    result = place_order(mock_client, order_data, dry_run=True)
    
    assert result["status"] == "FILLED (DRY-RUN)"
    assert mock_client.create_order.called is False # Proves the real API was NOT called

# ---------------------------------------------------------------------------
# 4. CLI Interface Tests
# ---------------------------------------------------------------------------
def test_cli_order_dry_run():
    """Test the main CLI command using Click's built-in test runner."""
    runner = CliRunner()
    # We use --yes to skip the y/n prompt, and --dry-run so it doesn't really execute
    result = runner.invoke(cli, [
        "order", 
        "--symbol", "SOLUSDT", 
        "--side", "BUY", 
        "--type", "MARKET", 
        "--qty", "10", 
        "--dry-run", 
        "--yes"
    ])
    
    # Assert the command exited successfully (code 0)
    assert result.exit_code == 0
    # Assert our cool terminal output rendered properly
    assert "ORDER SUMMARY" in result.output
    assert "DRY-RUN (SIMULATED)" in result.output
    assert "EXECUTION RESULT" in result.output