# Plan — Premier test WebApp Bundle Invest 1 USDC (Base)

| Champ | Valeur |
| --- | --- |
| **Statut** | **🟡 EN COURS — Go « WebApp Bundle Invest 1 USDC »** · baseline ✅ |
| **test_start_iso** | `2026-06-08T16:15:06.973194+00:00` |
| **Objectif** | Prouver le **dernier ~5 %** : Privy réel · signature · swap Base · confirmation · settlement économique réel |
| **Prérequis rails** | B4b ✅ · B5 ✅ · [GO_BUNDLE_B5_MINIMAL_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B5_MINIMAL_CONTROLLED_TEST_REPORT.md) |
| **Compte pilote** | `gaelitier@gmail.com` · Crypto Majors `ab4ae920-f3e8-481b-8f82-a41a81d5779d` |
| **Montant** | **1 USDC** |
| **Chaîne** | **Base** (8453) |

---

## Ce que ce test prouve (vs B4b/B5)

| Capacité | B4b/B5 ECS | WebApp 1 USDC |
| --- | --- | --- |
| Orchestration metadata | ✅ | ✅ attendu |
| Quote LI.FI réel | ✅ (B4b) | ✅ attendu |
| Signature Privy réelle | ❌ | **✅ requis** |
| Swap on-chain Base réel | ❌ (mock job) | **✅ requis** |
| Confirmation blockchain | ❌ | **✅ requis** |
| Settlement PE/CB réel | ❌ | **✅ requis** |

---

## Périmètre strict

**1 parent · 1 child · 1 leg BUY USDC→AAVE Base · 1 USDC**

**Interdit** : N legs · sell · rebalance · withdraw · flags ON permanents en TD · `LIFI_SWAPS_MOCK`.

---

## Checklist pré-test

- [x] Baseline prod : PE=19 · CB=67 · legs=131 · locks=0 · dead_letter=0 · `2026-06-08T16:15:06Z`
- [ ] Tous flags Bundle OFF en TD ECS
- [x] USDC disponible wallet pilote ≥ 1 USDC (**162.14**)
- [ ] Portfolio Crypto Majors actif WebApp
- [ ] Rollback documenté (intent IDs · batch_id)
- [ ] Fenêtre test annoncée · pas d'autres ops bundle pilote

---

## Flow attendu (WebApp)

```text
WebApp Bundle Invest (1 USDC · USDC entry · Base)
  → funding / lock (legacy ou event path selon wiring actuel)
  → parent intent + plan gelé
  → child #0 + swap LI.FI réel (Privy sign)
  → swap CONFIRMED on-chain (tx_hash réel)
  → child LEDGER_SETTLED (B3c si branché · ou legacy settlement)
  → parent RECONCILED (B5 si invoqué)
```

> **Note** : le wiring WebApp actuel peut encore passer par `BundleOrchestrator` legacy. Le test documentera **quel chemin** a été emprunté et si les metadata event-driven (parent/child · hashes) sont produits.

---

## Critères GO

- [ ] Invest WebApp complété sans intervention manuelle post-confirm
- [ ] `tx_hash` réel Base (pas mock `0xmock-b4b-…`)
- [ ] Child `LEDGER_SETTLED` ou équivalent legacy documenté
- [ ] Parent `RECONCILED` si B5 invoqué
- [ ] PE/CB/legs deltas cohérents avec ~1 USDC
- [ ] `dead_letter=0` · pas de lock orphelin
- [ ] Pas de double settlement

---

## Critères NO-GO / rollback

| Signal | Action |
| --- | --- |
| Swap bloqué signature | Stop · documenter · pas de retry aveugle |
| Lock orphelin | Release manuel `intent_id` parent |
| Double PE write | Stop · audit comptable |
| Parent COMPLETED non voulu | Documenter · pas de finalize |

Rollback : ne pas activer flags en TD · conserver intent IDs dans rapport · baseline PE/CB à re-vérifier.

---

## Séquence recommandée

1. ~~Go explicite « WebApp Bundle Invest 1 USDC »~~ ✅
2. ~~Baseline ECS~~ ✅ `all_checks_pass=true`
3. **Invest WebApp manuel** 1 USDC Crypto Majors (gaelitier)
4. Audit post-trade ECS :
   ```bash
   export BUNDLE_WEBAPP_TEST_START_ISO=2026-06-08T16:15:06.973194+00:00
   ./scripts/arquantix-ecs-bundle-webapp-invest-1usdc-test.sh post_trade_audit
   ```
5. Rapport [GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_REPORT.md](GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_REPORT.md)

**Seulement après GO WebApp** : envisager N legs · sell · rebalance.
