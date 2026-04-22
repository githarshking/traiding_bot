"""
Startup health-check: validates env vars and API connectivity
before the bot executes any order logic.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class HealthResult:
    name: str
    ok: bool
    detail: str


def check_env() -> HealthResult:
    key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_API_SECRET", "")
    if not key or not secret:
        return HealthResult(
            "Env Vars",
            False,
            "BINANCE_API_KEY and/or BINANCE_API_SECRET are missing",
        )
    if key == "your_testnet_api_key_here":
        return HealthResult("Env Vars", False, "Placeholder API key detected — update .env")
    return HealthResult("Env Vars", True, f"API key loaded ({key[:6]}...)")


def check_api(client) -> HealthResult:
    try:
        ok = client.ping()
        if ok:
            return HealthResult("API Ping", True, "Testnet reachable")
        return HealthResult("API Ping", False, "Ping returned False")
    except Exception as exc:
        return HealthResult("API Ping", False, str(exc))


def check_account(client) -> HealthResult:
    try:
        bal = client.get_usdt_balance()
        return HealthResult("Account", True, f"USDT balance: {bal:.4f}")
    except Exception as exc:
        return HealthResult("Account", False, str(exc))


def run_health_checks(client=None) -> list[HealthResult]:
    results = [check_env()]
    if client is not None:
        results.append(check_api(client))
        results.append(check_account(client))
    return results


def print_health_table(results: list[HealthResult]) -> bool:
    table = Table(title="[bold cyan]System Health Check[/bold cyan]", border_style="cyan")
    table.add_column("Check", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    all_ok = True
    for r in results:
        status = "[bold green]✓ OK[/bold green]" if r.ok else "[bold red]✗ FAIL[/bold red]"
        if not r.ok:
            all_ok = False
        table.add_row(r.name, status, r.detail)

    console.print(table)
    return all_ok
