#!/usr/bin/env bash
# Compare les quotes servies par l'API prod vs Binance public (sanity check).
set -euo pipefail

API_BASE="${API_BASE:-https://api.arquantix.com}"
SYMBOLS="${SYMBOLS:-BTCUSDT,ETHUSDT}"
MAX_DRIFT_PCT="${MAX_DRIFT_PCT:-2.0}"

python3 - <<'PY' "$API_BASE" "$SYMBOLS" "$MAX_DRIFT_PCT"
import json
import sys
import urllib.request

api_base, symbols_csv, max_drift = sys.argv[1], sys.argv[2], float(sys.argv[3])
symbols = [s.strip().upper() for s in symbols_csv.split(",") if s.strip()]

def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode())

failures = []
for sym in symbols:
    binance = fetch(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}")
    b_price = float(binance["price"])
    summary = fetch(f"{api_base}/api/market-data/market-summary?symbols={sym}")
    rows = summary.get("summaries") or []
    if not rows:
        failures.append(f"{sym}: absent de market-summary")
        continue
    a_price = float(rows[0]["price"])
    drift_pct = abs(a_price - b_price) / b_price * 100.0 if b_price else 100.0
    status = "OK" if drift_pct <= max_drift else "STALE"
    print(f"{sym}: api={a_price:.2f} binance={b_price:.2f} drift={drift_pct:.2f}% [{status}]")
    if drift_pct > max_drift:
        failures.append(f"{sym}: écart {drift_pct:.2f}% > {max_drift}%")

if failures:
    print("\nÉCHEC:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print("\nOK — quotes prod alignées avec Binance (seuil {:.1f}%).".format(max_drift))
PY
