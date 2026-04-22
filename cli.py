"""
cli.py — Main CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  python cli.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.01
  python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --qty 1.0 --price 3200
  python cli.py nlp "buy 0.01 BTC at market"
  python cli.py dashboard
  python cli.py strategies list
  python cli.py strategies run scalp_btc
  python cli.py logs --n 20 --level ERROR
  python cli.py health
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

# Force UTF-8 output on Windows to handle Rich emoji/unicode
import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.table import Table
from rich.text import Text

# Load .env from the trading_bot directory
_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()  # fall back to CWD

from bot.client import BinanceClient
from bot.orders import place_order
from bot.validators import validate_order
from bot.nlp_parser import parse_nlp_order
from bot.logging_config import get_logger, tail_logs
from bot.health_check import run_health_checks, print_health_table
from bot.strategies import get_strategy, list_strategies
from bot.dashboard import run_dashboard

console = Console()
logger = get_logger("cli")


# --- THEME CONSTANTS ---
C_BINANCE = "#F3BA2F"
C_CYAN = "#00FFFF"
C_MAGENTA = "#FF00FF"
C_DIM = "grey50"

def _get_client(dry_run: bool = False) -> BinanceClient | None:
    key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_API_SECRET", "")
    if dry_run and (not key or key == "your_testnet_api_key_here"):
        return None  # no real client needed for dry-run
    if not key or not secret:
        console.print(f"[bold {C_MAGENTA}]> ERR:[/bold {C_MAGENTA}] Missing API credentials.")
        sys.exit(1)
    return BinanceClient(api_key=key, api_secret=secret)

def _print_banner() -> None:
    # Cyberpunk / Minimalist Banner
    banner_text = f"""[{C_BINANCE}]      /\\      [/]
[{C_BINANCE}]     /  \\     [/]  [bold {C_CYAN}]BINANCE FUTURES TESTNET[/]
[{C_BINANCE}]    / /\\ \\    [/]  [{C_DIM}]TERMINAL v2.0 // NEON-DARK EDITION[/]
[{C_BINANCE}]   / /__\\ \\   [/]  [bold {C_MAGENTA}]> SYSTEM_STATUS: ONLINE[/]
[{C_BINANCE}]  /________\\  [/]"""
    console.print(Panel(banner_text, border_style=C_DIM, box=box.SQUARE))

def _order_summary_panel(order: dict, dry_run: bool) -> Panel:
    table = Table(box=box.MINIMAL, show_header=False, padding=(0, 2))
    table.add_column("Field", style=C_DIM)
    table.add_column("Value", style="bold white")
    table.add_row("Symbol", order["symbol"])
    side_color = "green" if order["side"] == "BUY" else "red"
    table.add_row("Side", f"[{side_color}]{order['side']}[/{side_color}]")
    table.add_row("Type", order["type"])
    table.add_row("Quantity", str(order["quantity"]))
    price_val = str(order["price"]) if order.get("price") else "MARKET PRICE"
    table.add_row("Price", price_val)
    if dry_run:
        table.add_row("Mode", f"[bold {C_MAGENTA}]DRY-RUN (SIMULATED)[/]")
    return Panel(table, title=f"[{C_CYAN}]> ORDER SUMMARY[/]", border_style=C_CYAN, box=box.SQUARE)

def _result_table(result: dict) -> None:
    table = Table(
        title=f"[{C_BINANCE}]> EXECUTION RESULT[/]",
        box=box.SIMPLE,
        border_style=C_DIM,
        show_header=True,
        header_style=f"bold {C_CYAN}",
    )
    table.add_column("Key")
    table.add_column("Value", style="bold white")
    fields = [
        ("orderId", "Order ID"),
        ("status", "Status"),
        ("symbol", "Symbol"),
        ("side", "Side"),
        ("type", "Type"),
        ("executedQty", "Exec Qty"),
        ("avgPrice", "Avg Price"),
    ]
    for key, label in fields:
        val = result.get(key, "—")
        table.add_row(label, str(val))
    console.print(table)


# ---------------------------------------------------------------------------
# CLI groups
# ---------------------------------------------------------------------------


@click.group()
def cli():
    """Binance Futures Testnet Trading Bot CLI"""
    pass


# ------------------------------------------------------------------
# order command
# ------------------------------------------------------------------

@cli.command()
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--type", "order_type", required=True, type=click.Choice(["MARKET", "LIMIT"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--price", default=None, type=float)
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--yes", "-y", is_flag=True, default=False)
def order(symbol, side, order_type, qty, price, dry_run, yes):
    _print_banner()
    try:
        validated = validate_order(symbol, side, order_type, qty, price)
    except ValueError as exc:
        console.print(f"[bold {C_MAGENTA}]> VALIDATION ERR:[/] {exc}")
        sys.exit(1)

    console.print(_order_summary_panel(validated, dry_run))
    if not yes:
        if not Confirm.ask(f"[bold {C_BINANCE}]> PROCEED?[/]"):
            console.print(f"[{C_DIM}]> Aborted.[/]")
            return

    client = _get_client(dry_run=dry_run)
    with Status(f"[bold {C_CYAN}]> TRANSMITTING PAYLOAD...[/]", spinner="bouncingBar"):
        try:
            result = place_order(client, validated, dry_run=dry_run)
        except Exception as exc:
            console.print(f"[bold {C_MAGENTA}]> EXEC ERR:[/] {exc}")
            sys.exit(1)
    _result_table(result)


# ------------------------------------------------------------------
# nlp command
# ------------------------------------------------------------------

@cli.command()
@click.argument("text")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--yes", "-y", is_flag=True, default=False)
def nlp(text, dry_run, yes):
    _print_banner()
    console.print(f"[{C_DIM}]> AI PARSING:[/] [italic]{text}[/]\n")
    try:
        parsed = parse_nlp_order(text)
        validated = validate_order(parsed["symbol"], parsed["side"], parsed["type"], parsed["quantity"], parsed.get("price"))
    except Exception as exc:
        console.print(f"[bold {C_MAGENTA}]> PARSE ERR:[/] {exc}")
        sys.exit(1)

    console.print(_order_summary_panel(validated, dry_run))
    if not yes:
        if not Confirm.ask(f"[bold {C_BINANCE}]> EXECUTE AI ORDER?[/]"):
            return

    client = _get_client(dry_run=dry_run)
    with Status(f"[bold {C_CYAN}]> TRANSMITTING PAYLOAD...[/]", spinner="bouncingBar"):
        result = place_order(client, validated, dry_run=dry_run)
    _result_table(result)

# ------------------------------------------------------------------
# dashboard command
# ------------------------------------------------------------------

@cli.command()
@click.option("--refresh", default=5)
def dashboard(refresh):
    _print_banner()
    client = _get_client()
    run_dashboard(client, refresh=refresh)


# ------------------------------------------------------------------
# health command
# ------------------------------------------------------------------

@cli.command()
def health():
    """Run startup health checks (env vars + API connectivity)."""
    _print_banner()
    client = None
    try:
        client = _get_client()
    except SystemExit:
        pass
    results = run_health_checks(client)
    ok = print_health_table(results)
    if not ok:
        sys.exit(1)


# ------------------------------------------------------------------
# strategies command group
# ------------------------------------------------------------------

@cli.group()
def strategies():
    """Manage and run named strategy presets."""
    pass


@strategies.command("list")
def strategies_list():
    """List all available strategy presets."""
    _print_banner()
    try:
        strats = list_strategies()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    table = Table(
        title="[bold cyan]Strategy Presets[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white",
    )
    table.add_column("Key", style="bold yellow")
    table.add_column("Name")
    table.add_column("Symbol")
    table.add_column("Side")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Description", style="dim")

    for s in strats:
        side_color = "green" if s["side"] == "BUY" else "red"
        table.add_row(
            s["key"],
            s["name"],
            s["symbol"],
            f"[{side_color}]{s['side']}[/{side_color}]",
            s["type"],
            str(s["quantity"]),
            str(s["price"]),
            s["description"],
        )
    console.print(table)


@strategies.command("run")
@click.argument("name")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--yes", "-y", is_flag=True, default=False)
def strategies_run(name, dry_run, yes):
    """Execute a named strategy preset."""
    _print_banner()
    try:
        validated = get_strategy(name)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]✗ Strategy error:[/bold red] {exc}")
        sys.exit(1)

    console.print(f"[bold cyan]Strategy:[/bold cyan] [yellow]{name}[/yellow]\n")
    console.print(_order_summary_panel(validated, dry_run))

    if not yes:
        confirmed = Confirm.ask("[bold yellow]Run this strategy?[/bold yellow]")
        if not confirmed:
            console.print("[yellow]Strategy cancelled.[/yellow]")
            return

    client = _get_client(dry_run=dry_run)
    with Status("[bold cyan]Executing strategy...[/bold cyan]", spinner="dots"):
        try:
            result = place_order(client, validated, dry_run=dry_run)
        except Exception as exc:
            console.print(f"[bold red]✗ Strategy failed:[/bold red] {exc}")
            sys.exit(1)

    _result_table(result)


# ------------------------------------------------------------------
# logs command
# ------------------------------------------------------------------

@cli.command()
@click.option("--n", default=50, help="Number of recent log entries to show")
@click.option("--level", default=None, help="Filter by log level (INFO, WARNING, ERROR)")
def logs(n, level):
    """View structured JSONL log entries."""
    _print_banner()
    records = tail_logs(n=n, level_filter=level)

    if not records:
        console.print("[dim]No log entries found.[/dim]")
        return

    table = Table(
        title=f"[bold cyan]Last {len(records)} Log Entries[/bold cyan]",
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        header_style="bold white",
    )
    table.add_column("Timestamp", style="dim", no_wrap=True)
    table.add_column("Level", justify="center")
    table.add_column("Logger", style="dim")
    table.add_column("Message")

    level_styles = {
        "INFO": "bold green",
        "WARNING": "bold yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
        "DEBUG": "dim",
    }

    for rec in records:
        lvl = rec.get("level", "INFO")
        style = level_styles.get(lvl, "white")
        table.add_row(
            rec.get("ts", "?")[:19].replace("T", " "),
            f"[{style}]{lvl}[/{style}]",
            rec.get("logger", "?"),
            rec.get("msg", ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
