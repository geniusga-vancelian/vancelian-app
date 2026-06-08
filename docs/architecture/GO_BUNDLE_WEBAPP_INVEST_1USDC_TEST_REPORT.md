# Rapport — WebApp Bundle Invest (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Portfolio** | Crypto Majors `ab4ae920-f3e8-481b-8f82-a41a81d5779d` |
| **Plan initial** | [GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md](GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md) |
| **test_start_iso** | `2026-06-08T16:15:06.973194+00:00` |
| **Décision** | **🟡 GO opérationnel partiel — pas GO strict plan 1 USDC** |

---

## 1. Décision

**Le dernier morceau réel est partiellement prouvé** : signature Privy + swap Base **réel** confirmé pour au moins **1 leg** (CBBTC), tx on-chain non-mock, settlement économique CB **+7**.

**Pas GO strict** du plan initial (1 USDC · 1 leg · rail event-driven) : invest WebApp réel **~20 USDC · 5 legs · chemin legacy orchestrator**.

**Écart UI / DB** : l’écran « Terminée · 5/5 legs » (capture 20:23) ne correspond pas entièrement à l’état DB du batch audité au même moment — à clarifier (batch historique vs invest en cours).

---

## 2. Baseline (pré-test) — ✅

| Check | Valeur |
| --- | --- |
| `all_checks_pass` | **true** |
| PE / CB / legs | **19 / 67 / 131** |
| USDC wallet | **162.14** |

---

## 3. Invest WebApp observé

| Élément | Valeur |
| --- | --- |
| Montant saisi UI | **20 USDC** |
| Montant alloué UI (écran détail) | **~19 USDC** |
| Legs UI | **5** (CBBTC · CBETH · LINK · AAVE · UNI) |
| Chemin | **Legacy `BundleOrchestrator`** (pas B4b/B5 event-driven) |
| Statut UI (capture) | **Terminée** · 5/5 legs · LI.FI confirmées |

---

## 4. Audit ECS post-trade (batch `10d688bb-b625-46ec-b8dd-570f158b844a`)

| Champ | Valeur |
| --- | --- |
| `parent_intent_id` | `5ad2670d-5f75-457a-bef5-d4f4d1e630dc` |
| `batch_id` | `10d688bb-b625-46ec-b8dd-570f158b844a` |
| `parent_status` (DB) | **`partial`** |
| `execution_path` | `legacy_orchestrator_metadata` |

### Swaps (état DB au audit)

| Asset | Swap ID | Statut DB | tx_hash |
| --- | --- | --- | --- |
| CBBTC | `07f68bb2-…` | **CONFIRMED** | `0xef941cc237f33d31e63bf2f9c5a57b1a6782f9e9f9456f57a67a38c9241a85ce` |
| CBETH | `cc773300-…` | **SUBMITTED** | `0x36228d0c5719143b6fc9cab925a5222f7daa7c950a260cdbee9640870f6f5740` |
| LINK | `03e385e2-…` | QUOTE_RECEIVED | — |
| AAVE | `a2dff04c-…` | QUOTE_RECEIVED | — |
| UNI | `32ccfa9c-…` | QUOTE_RECEIVED | — |

### Économie

| Métrique | Baseline | Post-audit | Δ |
| --- | --- | --- | --- |
| PE | 19 | 19 | 0 |
| CB | 67 | **74** | **+7** |
| legs | 131 | 131 | 0 |
| dead_letter | 0 | 0 | 0 |
| locks | 0 | 0 | 0 |

---

## 5. Critères — bilan

| Critère | Statut | Note |
| --- | --- | --- |
| `tx_hash` réel (pas mock) | ✅ (≥1 leg) | CBBTC + CBETH tx réels |
| Signature Privy réelle | ✅ (inféré) | SUBMITTED/CONFIRMED on-chain |
| Tous swaps CONFIRMED (5/5) | ⚠️ | DB : **1/5** au moment audit |
| PE/CB/legs cohérents | ✅ partiel | CB **+7** · PE stable |
| `dead_letter=0` | ✅ | |
| Lock orphelin = 0 | ✅ | |
| Pas de double settlement | ✅ | `duplicate_leg_deposit_keys=0` |
| Rail event-driven B4b/B5 | ❌ | Legacy attendu WebApp actuel |

---

## 6. Ce que ce test prouve

| Prouvé | Non prouvé (encore) |
| --- | --- |
| WebApp → LI.FI → Privy → tx Base **réelle** | 5/5 legs CONFIRMED en DB (sync) |
| `bundle_execution=true` · `bundle_internal` | Rail event-driven 1×1×1 |
| Écritures CB réelles (+7) | Parent RECONCILED B5 |
| Pas de mock `0xmock-b4b-…` sur ce batch | Plan strict 1 USDC |

---

## 7. Prochaines actions

1. **Re-audit** dans 15–30 min (metadata parent + swaps CONFIRMED) :
   ```bash
   export BUNDLE_WEBAPP_TEST_START_ISO=2026-06-08T16:15:06.973194+00:00
   ./scripts/arquantix-ecs-bundle-webapp-invest-1usdc-test.sh post_trade_audit
   ```
2. Confirmer si l’écran « Terminée » correspond au batch `10d688bb…` ou à une allocation historique (montants UI ≠ montants batch audit).
3. Si 5/5 CONFIRMED en DB → passer décision à **GO opérationnel complet**.
4. **Ne pas** ouvrir N legs event-driven tant que le strict 1 USDC event-driven n’a pas été tenté séparément.

---

## 8. Position CTO

Le laboratoire B1→B5 est **validé**. Le WebApp legacy prouve déjà le **chaînon réel blockchain** (Privy + LI.FI + settlement CB).

Le prochain chantier produit : soit **attendre sync 5/5** sur ce run 20 USDC, soit **re-run contrôlé 1 USDC** sur rail event-driven quand WebApp sera branché sur B4b.
