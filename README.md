# ⚡ Binance Futures Testnet Trading Bot

A production-ready Python CLI trading terminal for Binance Futures Testnet (USDT-M), featuring a live Rich TUI dashboard, NLP order parsing, dry-run simulation, strategy presets, and structured log viewing.

---

## 🗂 Project Structure

```
trading_bot/
├── bot/
│   ├── client.py           # Authenticated Binance REST API wrapper
│   ├── orders.py           # Order building, dry-run simulation & placement
│   ├── validators.py       # Strict input validation
│   ├── nlp_parser.py       # Natural language → structured order
│   ├── logging_config.py   # JSONL structured logging
│   ├── dashboard.py        # Live Rich TUI dashboard engine
│   ├── strategies.py       # Strategy preset loader
│   └── health_check.py     # Startup API/env health validator
├── strategies.yaml         # Named strategy definitions
├── cli.py                  # CLI entry point
├── .env.example            # Required env var template
└── requirements.txt        # Pinned dependencies
```

---

## ⚙️ Setup

### 1. Get Testnet API Keys
1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com/)
2. Log in → API Management → Generate Key

### 2. Install Dependencies
```bash
cd trading_bot
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in your BINANCE_API_KEY and BINANCE_API_SECRET
```

---

## 🚀 Usage

### Place a Market Order
```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.01
```

### Place a Limit Order
```bash
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --qty 1.0 --price 3200
```

### Dry-Run (Simulate, No Real Order)
```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.01 --dry-run
```

### Natural Language Order
```bash
python cli.py nlp "buy 0.01 BTC at market"
python cli.py nlp "sell 1 ETH limit at 3200"
python cli.py nlp "long 0.5 BNB"
```

### Live Dashboard
```bash
python cli.py dashboard
python cli.py dashboard --refresh 10   # refresh every 10 seconds
```

### Health Check
```bash
python cli.py health
```

### Strategy Presets
```bash
python cli.py strategies list
python cli.py strategies run scalp_btc
python cli.py strategies run scalp_btc --dry-run
```

### View Logs
```bash
python cli.py logs
python cli.py logs --n 20
python cli.py logs --level ERROR
```

---

## 🛡 Safety Features

| Feature | Description |
|:--------|:------------|
| **Dry-Run Mode** | `--dry-run` flag simulates order placement with a realistic fake response |
| **Confirmation Prompt** | Every order shows a summary panel and requires explicit confirmation |
| **Input Validation** | All inputs validated (symbol suffix, quantity bounds, LIMIT price requirement) |
| **Health Check** | Validates env vars and API connectivity before any operation |
| **Structured Logs** | All activity written to `logs/trading_bot.jsonl` for audit trail |

---

## 📋 Environment Variables

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `BINANCE_API_KEY` | ✅ | — | Testnet API key |
| `BINANCE_API_SECRET` | ✅ | — | Testnet API secret |
| `BINANCE_BASE_URL` | ❌ | `https://testnet.binancefuture.com` | API base URL |
| `DRY_RUN` | ❌ | `false` | Global dry-run override |
| `LOG_FILE` | ❌ | `logs/trading_bot.jsonl` | Log output path |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity |

---

## 📈 Strategy Presets

Edit `strategies.yaml` to define named presets:

```yaml
strategies:
  my_strategy:
    name: "My BTC Long"
    symbol: BTCUSDT
    side: BUY
    type: MARKET
    quantity: 0.001
    description: "Quick market long"
```

Then run:
```bash
python cli.py strategies run my_strategy --dry-run
```

---

## ⚠️ Disclaimer

This bot connects to **Binance Futures Testnet** only. Never use real production API keys. All trading involves risk. This is for educational purposes.
