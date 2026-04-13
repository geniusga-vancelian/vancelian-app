# Diagnostic Market Data + Backtest

**Date** : 2026-01-08T14:46:50.111884
**Mode** : quick
**Database** : arquantix_quant
**Duration** : 141 ms

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS | 5 |
| ❌ FAIL | 0 |
| ⏭️ SKIP | 1 |
| **Total** | **6** |

## Checks Detail

### 1. Router Availability - ✅ PASS

**Details:**
- ✓ Market Data router importable
- ✓ Backtest router importable

---

### 2. Instruments Exist - ✅ PASS

**Details:**
- ✓ 10 instruments available

**Duration:** 3 ms

- Count before: 10
- Count after: 10
---

### 3. Bars Existence - ✅ PASS

**Details:**
- Global date range: 2025-09-10 to 2026-01-08
- ⚠ QQQ: 0 bars
- ⚠ DIA: 0 bars
- ⚠ ACWI: 0 bars
- ⚠ GLD: 0 bars
- ⚠ ETH: 0 bars
- ⚠ SOL: 0 bars
- ⚠ BNB: 0 bars
- ⚠ XRP: 0 bars
- ✓ 2/10 instruments have bars

**Duration:** 19 ms

- Total bars: 204
- Date min: 2025-09-10
- Date max: 2026-01-08
**Instruments detail:**

| Symbol | Bars | Date Min | Date Max |
|--------|------|----------|----------|
| SPY | 83 | 2025-09-10 | 2026-01-07 |
| QQQ | 0 | N/A | N/A |
| DIA | 0 | N/A | N/A |
| ACWI | 0 | N/A | N/A |
| GLD | 0 | N/A | N/A |
| BTC | 121 | 2025-09-10 | 2026-01-08 |
| ETH | 0 | N/A | N/A |
| SOL | 0 | N/A | N/A |
| BNB | 0 | N/A | N/A |
| XRP | 0 | N/A | N/A |

---

### 4. Quick Backfill - ⏭️ SKIP

**Details:**
- Skipped: sufficient bars exist

---

### 5. Backtest Run Minimal - ✅ PASS

**Details:**
- Running backtest: 2025-10-10 to 2026-01-08
- ✓ NAV series length: 90
- ✓ NAV[0] = 100.000000
- ✓ Max drawdown: -0.1740
- ✓ No NaN in series
- ✓ Backtest run 2 completed successfully

**Duration:** 79 ms

- Backtest Run ID: 2
- Effective start: 2025-10-10
- Effective end: 2026-01-07
**Metrics:**
- CAGR: -36.58%
- Volatility: 23.34%
- Sharpe: -0.09
- Max Drawdown: -17.40%
- Calmar: -2.10

---

### 6. API Endpoints - ✅ PASS

**Details:**
- ✓ /api/market-data/instruments endpoint exists
- ✓ /api/backtests/instruments endpoint exists

**Duration:** 21 ms

---

## Recommendations

⚠️ **Warnings:** Some checks have warnings. Review details above.

---

*Generated at 2026-01-08T14:46:50.111884*