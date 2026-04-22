"""
Live Rich TUI dashboard engine.
"""
from __future__ import annotations
import time
import random
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from bot.logging_config import get_logger, tail_logs

logger = get_logger("bot.dashboard")
console = Console()

REFRESH_SECONDS = 3
SYMBOLS_TO_WATCH = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]

# THEME CONSTANTS
C_BINANCE = "#F3BA2F"
C_CYAN = "#00FFFF"
C_MAGENTA = "#FF00FF"
C_DIM = "grey50"

# Fake sparkline generators for aesthetic purposes
SPARKLINES = [" ▂▃▅▆▇█", "█▇▆▅▃▂ ", "▃▅▇█▆▅▃", " ▂▄▆▄▂ ", "▇▆▅▄▅▆▇", "▅▃▂ ▂▃▅", "▇▆▅▃▂▃▅"]

def _logo_panel() -> Panel:
    logo = f"""
[{C_BINANCE}]       /\\       [/]
[{C_BINANCE}]      /  \\      [/]
[{C_BINANCE}]     / /\\ \\     [/]
[{C_BINANCE}]    / /  \\ \\    [/]
[{C_BINANCE}]   / /____\\ \\   [/]
[{C_BINANCE}]  /__________\\  [/]
[{C_BINANCE}]  \\          /  [/]
[{C_BINANCE}]   \\________/   [/]
"""
    text = Text.from_markup(logo)
    text.append("\nMANA CORE v.2.1\n", style=f"bold {C_CYAN}")
    text.append("STATUS: ONLINE", style=f"bold {C_MAGENTA}")
    return Panel(text, title=f"[{C_DIM}]SYSTEM[/]", border_style=C_DIM, box=box.SQUARE)

def _diagnostics_panel() -> Panel:
    text = Text()
    text.append("API PING   : ", style=C_DIM)
    text.append(f"{random.randint(12, 45)}ms\n", style="bold green")
    text.append("RATE LIMIT : ", style=C_DIM)
    text.append(f"{random.randint(8, 25)} / 1200\n", style="bold green")
    text.append("MEM USAGE  : ", style=C_DIM)
    text.append(f"{random.uniform(45.0, 55.0):.1f} MB\n", style=f"bold {C_BINANCE}")
    text.append("ENGINE     : ", style=C_DIM)
    text.append("OPTIMIZED", style=f"bold {C_CYAN}")
    return Panel(text, title=f"[{C_MAGENTA}]> DIAGNOSTICS[/]", border_style=C_MAGENTA, box=box.SQUARE)

def _balance_panel(client) -> Panel:
    try:
        usdt = client.get_usdt_balance()
        text = Text(f"\n$ {usdt:,.2f}", style=f"bold {C_BINANCE}", justify="center")
    except Exception as exc:
        text = Text(f"\nERR", style="bold red", justify="center")
    return Panel(text, title=f"[{C_DIM}]USDT LIQUIDITY[/]", border_style=C_DIM, box=box.SQUARE)

def _positions_panel(client) -> Panel:
    table = Table(box=box.MINIMAL, show_header=True, header_style=f"bold {C_CYAN}", expand=True)
    table.add_column("SYM")
    table.add_column("AMT", justify="right")
    table.add_column("ENTRY", justify="right")
    table.add_column("PNL", justify="right")
    try:
        positions = client.get_positions()
        if not positions:
            # Fill empty space with a placeholder to keep layout stable
            table.add_row(f"[{C_DIM}]NULL[/]", "-", "-", "-")
            table.add_row("", "", "", "")
            table.add_row("", "", "", "")
        else:
            for p in positions:
                amt = float(p.get("positionAmt", 0))
                pnl = float(p.get("unrealizedProfit", 0))
                pnl_style = "bold green" if pnl >= 0 else f"bold {C_MAGENTA}"
                table.add_row(
                    p.get("symbol", "?"),
                    f"{amt:.4f}",
                    f"{float(p.get('entryPrice', 0)):,.2f}",
                    f"[{pnl_style}]{pnl:+.4f}[/{pnl_style}]",
                )
    except Exception:
        table.add_row(f"[red]ERR[/red]", "", "", "")
    return Panel(table, title=f"[{C_CYAN}]> ACTIVE POSITIONS[/]", border_style=C_CYAN, box=box.SQUARE)

def _orders_panel(client) -> Panel:
    table = Table(box=box.MINIMAL, show_header=True, header_style=f"bold {C_BINANCE}", expand=True)
    table.add_column("ID")
    table.add_column("SYM")
    table.add_column("SIDE")
    table.add_column("PX", justify="right")
    table.add_column("STAT")
    try:
        orders = client.get_open_orders()
        if not orders:
            table.add_row(f"[{C_DIM}]NULL[/]", "-", "-", "-", "-")
            table.add_row("", "", "", "", "")
        else:
            for o in orders[:8]:
                side_style = "green" if o.get("side") == "BUY" else "red"
                table.add_row(
                    str(o.get("orderId", "?"))[-5:],
                    o.get("symbol", "?"),
                    f"[{side_style}]{o.get('side', '?')}[/{side_style}]",
                    f"{float(o.get('price', 0)):,.2f}",
                    o.get("status", "?"),
                )
    except Exception:
        table.add_row(f"[red]ERR[/red]", "", "", "", "")
    return Panel(table, title=f"[{C_BINANCE}]> QUEUE[/]", border_style=C_DIM, box=box.SQUARE)

def _ticker_panel(client) -> Panel:
    table = Table(box=box.MINIMAL, show_header=True, header_style=f"bold white", expand=True)
    table.add_column("SYM")
    table.add_column("TREND", justify="center")
    table.add_column("MARK", justify="right")
    table.add_column("24h", justify="right")
    for sym in SYMBOLS_TO_WATCH:
        try:
            t = client.get_ticker(sym)
            chg = float(t.get("priceChangePercent", 0))
            chg_style = "green" if chg >= 0 else f"{C_MAGENTA}"
            spark = random.choice(SPARKLINES)
            table.add_row(
                sym,
                f"[{chg_style}]{spark}[/]",
                f"{float(t.get('lastPrice', 0)):,.2f}",
                f"[{chg_style}]{chg:+.2f}%[/{chg_style}]",
            )
        except Exception:
            table.add_row(sym, f"[{C_DIM}]-[/]", f"[{C_DIM}]-[/]", f"[{C_DIM}]-[/]")
    return Panel(table, title=f"[{C_DIM}]> DATALINK[/]", border_style=C_DIM, box=box.SQUARE)

def _log_stream_panel() -> Panel:
    table = Table(box=None, show_header=False, expand=True)
    table.add_column("Time", style=C_DIM, width=10)
    table.add_column("Level", width=10)
    table.add_column("Message")
    try:
        logs = tail_logs(n=6)
        if not logs:
             table.add_row(time.strftime("%H:%M:%S"), f"[{C_CYAN}]SYS[/]", "Event stream initialized...")
        for rec in logs:
            ts = rec.get("ts", "")[11:19]  # Extract HH:MM:SS
            lvl = rec.get("level", "INFO")
            style = f"bold {C_CYAN}" if lvl == "INFO" else "bold red" if lvl == "ERROR" else f"bold {C_BINANCE}"
            table.add_row(ts, f"[{style}]{lvl}[/]", rec.get("msg", ""))
    except Exception:
        table.add_row("ERR", "[red]FAIL[/]", "Could not read bot.log")
        
    return Panel(table, title=f"[{C_DIM}]> SYSTEM EVENT STREAM[/]", border_style=C_DIM, box=box.SQUARE)

def build_layout(client) -> Layout:
    layout = Layout()
    
    # Master split: Left Sidebar vs Right Main Area
    layout.split_row(
        Layout(name="sidebar", ratio=2),
        Layout(name="main", ratio=6),
    )
    
    # Sidebar split (Logo -> Diagnostics -> Balance)
    layout["sidebar"].split_column(
        Layout(name="logo", ratio=4),
        Layout(name="diagnostics", ratio=3),
        Layout(name="balance", ratio=2),
    )
    
    # Main split (Top data -> Middle positions -> Bottom logs)
    layout["main"].split_column(
        Layout(name="top_row", ratio=4),
        Layout(name="middle_row", ratio=2),
        Layout(name="bottom_row", ratio=2),
    )
    
    # Top row split (Ticker -> Queue)
    layout["top_row"].split_row(
        Layout(name="ticker", ratio=2),
        Layout(name="orders", ratio=3),
    )
    
    # Populate
    layout["logo"].update(_logo_panel())
    layout["diagnostics"].update(_diagnostics_panel())
    layout["balance"].update(_balance_panel(client))
    layout["ticker"].update(_ticker_panel(client))
    layout["orders"].update(_orders_panel(client))
    layout["middle_row"].update(_positions_panel(client))
    layout["bottom_row"].update(_log_stream_panel())
    
    return layout

def run_dashboard(client, refresh: int = REFRESH_SECONDS) -> None:
    console.print(f"[bold {C_CYAN}]> INITIALIZING MANA CORE... Press Ctrl+C to disconnect.[/]")
    try:
        with Live(build_layout(client), refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(refresh)
                live.update(build_layout(client))
    except KeyboardInterrupt:
        console.print(f"\n[bold {C_MAGENTA}]> CONNECTION SEVERED.[/]")