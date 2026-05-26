# Rapport Phase 2 — Portal Webapp (LI.FI Bundle)

**Date :** 2026-05-26  
**Statut :** Implémenté côté web BFF + UI · **pilote E2E Docker bloqué** (image API à reconstruire)  
**Priorité validée :** Portal / BFF Next.js — pas Flutter

---

## A. Diagnostic

| Zone | État |
|------|------|
| Routes BFF `/api/portal/bundles/*` | Présentes · répondent **401** sans session (Next `:3000` OK) |
| UI Marchés → Invest | Modale `PortalBundleInvestDialog` + `useBundleLifiInvest` |
| FastAPI bundle LI.FI (Docker recovery) | Image **`arquantixrecovery-arquantix-api-1` sans module `bundle_execution`** — code Phase 1/2 absent du conteneur |
| Variables pilote dans conteneur API | Seul `LIFI_SWAPS_MOCK=1` · **`BUNDLE_EXECUTION_PROVIDER` non défini** |
| Pytest ciblé (hôte Python 3.9) | Collection **bloquée** par `TypeError` dans `test_clients/service.py` (`int \| None`) via import `main` |
| Pytest Phase 2 (sans conftest) | **6/6 OK** |
| Pytest Phase 1 (sans conftest) | **4/6 OK**, 1 failed (signature `_execute_swap`), 2 errors (fixtures DB) |
| `tsc --noEmit` (web) | Erreurs **préexistantes** hors scope bundle · **aucune erreur** sur fichiers bundle/portal ajoutés |
| Test web bundle routes | `bundleClient.routes.test.ts` — vérifie chemins BFF + pas de `submitSwapTx` |

---

## B. Cause probable (pilote Docker incomplet)

1. **Image API non rebuild** après ajout de `services/portfolio_engine/bundle_execution/` → invest reste sur le chemin **Exchange** (`insufficient_crypto_balance` sur `crypto_positions`, pas de `pending_signature` / `execution_provider: lifi_base`).
2. **`BUNDLE_EXECUTION_PROVIDER=lifi_base`** non injecté dans le service Compose (uniquement passable à la main sur `docker exec` une fois l’image à jour).
3. Pytest global sur macOS **Python 3.9** : régression connue, non liée au bundle.

---

## C. Routes BFF Portal

Toutes passent par `portalUpstreamFetch` → `buildBackendUrl('/api/app/...')` (JWT cookie portail). **Aucun appel browser → FastAPI direct.**

| Route Next.js | Méthode | Upstream FastAPI |
|---------------|---------|------------------|
| `/api/portal/bundles/invest` | POST | `/api/app/bundle/invest` |
| `/api/portal/bundles/invest/preview` | POST | `/api/app/bundle/invest/preview` |
| `/api/portal/bundles/leg/[swapId]/prepare-sign` | POST | `/api/app/bundle/leg/{swap_id}/prepare-sign` |
| `/api/portal/bundles/leg/[swapId]/submit-tx` | POST | `/api/app/bundle/leg/{swap_id}/submit-tx` |
| `/api/portal/bundles/batch/finalize` | POST | `/api/app/bundle/batch/finalize` |

**Non utilisé pour le submit bundle :** `POST /api/portal/swaps/[swapId]` (swap self-trading).

Fichiers :

- `services/arquantix/web/src/app/api/portal/bundles/**`
- `services/arquantix/web/src/lib/portal/bundleClient.ts`
- `services/arquantix/web/src/components/portal/bundles/useBundleLifiInvest.ts`
- `services/arquantix/web/src/components/portal/bundles/PortalBundleInvestDialog.tsx`

---

## D. Flow UI exact

```text
Marchés (/app/markets)
  → GET /api/portal/markets
      → upstream GET /api/app/bundle/catalog (portfolio_id, entry_asset_*)
  → Crypto Bundles → Invest (si portfolioId)
  → PortalBundleInvestDialog
      1. POST /api/portal/bundles/invest/preview
      2. POST /api/portal/bundles/invest
      3. Si status pending_signature | partial_pending :
           pour chaque leg pending (swap_id) :
             signing embarqué OU POST .../prepare-sign
             Privy sign (useLifiSwapExecution + submitBundleLegTx)
             poll GET /api/portal/swaps/{swapId}  (statut terminal)
      4. POST /api/portal/bundles/batch/finalize
           { portfolio_id, batch_id, entry_instrument_id,
             planned_entry_total, entry_consumed }
      5. invalidatePortalCache (markets, crypto-wallet, dashboard)
```

**Bundle pilote local (TOP_5 = 60 % BTC / 40 % ETH)** : produit `TOP_5` en base `arquantix_fresh`, pas un libellé UI « 60/40 » séparé.

---

## E. Variables d’environnement pilote

```env
BUNDLE_EXECUTION_PROVIDER=lifi_base
LIFI_SWAPS_ENABLED=1
LIFI_SWAPS_MOCK=1
BUNDLE_LIFI_SYNC_MOCK=1   # optionnel — auto-complete legs en dev
```

Côté web (complément mock backend) : `LIFI_LOCAL_SANDBOX_ENABLED=true` (dev only) + `catalog.mock_mode` via `GET /api/portal/swaps/supported-assets`.

**Action requise avant pilote E2E réussi :** rebuild + redémarrage `arquantix-api` avec les variables ci-dessus (validation explicite `.env.arquantix` / Compose selon charte environnement).

---

## F. Vérifications attendues (checklist pilote)

- [ ] `portfolio_id` présent sur carte bundle (catalog enrichi)
- [ ] `entry_instrument_id` dans réponse invest LI.FI
- [ ] Chaque leg `pending` a un `swap_id`
- [ ] Network tab : uniquement `/api/portal/bundles/...` + **GET** `/api/portal/swaps/{id}` (poll) — pas de POST swap submit
- [ ] `pe_position_atoms` : pas de crédit sur quote/prepare ; après submit confirmé + finalize
- [ ] `invariant_g` dans réponse `finalize` (dry-run, non bloquant)
- [ ] Pas d’appel vers `api.arquantix.com` / `:8000` depuis le browser (uniquement origin Next)

---

## G. Résultats de tests exécutés (2026-05-26)

### Backend (hôte, Python 3.9)

```bash
cd services/arquantix/api
BUNDLE_EXECUTION_PROVIDER=lifi_base LIFI_SWAPS_MOCK=1 \
  python3 -m pytest tests/test_bundle_orchestrator.py \
  tests/test_bundle_execution_adapter_phase1.py \
  tests/test_bundle_lifi_phase2.py -q
# → 21 errors (import main → test_clients/service.py int | None)
```

```bash
PYTHONPATH=. python3 -m pytest tests/test_bundle_lifi_phase2.py --noconftest -q
# → 6 passed
```

```bash
PYTHONPATH=. python3 -m pytest tests/test_bundle_execution_adapter_phase1.py --noconftest -q
# → 4 passed, 1 failed, 2 errors
```

### Script pilote Docker

```bash
docker cp services/arquantix/api/scripts/pilot_bundle_lifi_invest_mock.py \
  arquantixrecovery-arquantix-api-1:/app/scripts/
docker exec -w /app -e PYTHONPATH=/app \
  -e BUNDLE_EXECUTION_PROVIDER=lifi_base \
  -e LIFI_SWAPS_ENABLED=1 -e LIFI_SWAPS_MOCK=1 -e BUNDLE_LIFI_SYNC_MOCK=1 \
  arquantixrecovery-arquantix-api-1 \
  python3 scripts/pilot_bundle_lifi_invest_mock.py --amount 25 --asset USDC
```

**Résultat :** échec — module `services.portfolio_engine.bundle_execution` **absent** de l’image ; avec ancien code, invest Exchange → `insufficient_crypto_balance` (pas de USDC wallet simulé).

### Web

```bash
cd services/arquantix/web
npx tsc --noEmit   # erreurs préexistantes (ledgity/morpho tests) — rien sur bundle
node --import tsx --test src/lib/portal/bundleClient.routes.test.ts
# → OK
```

`pnpm test` : pas de script racine unique ; suites ciblées via `test:*` dans `package.json`.

---

## H. Verrou anti-double investissement (2026-05-26)

- **Backend** : `bundle_invest_lock` dans `pe_portfolios.metadata` · clé `client_id + portfolio_id + invest`.
- Statuts actifs : `pending_signature`, `signature_requested`, `submitted`, `pending_confirmation`, `finalizing`, `partial_pending`.
- **POST invest** : `409` + `{ status: "already_pending", batch_id, message }` si verrou actif.
- **GET** `/api/app/bundle/invest/active-lock?portfolio_id=` → reprise Portal après refresh.
- **Portal** : garde `inFlightRef`, sessionStorage, confirm fermeture modale, libellés d’état FR.
- **Tests** : `tests/test_bundle_invest_lock.py` (7 passed, `--noconftest`).

---

## I. Limites connues

| Limite | Détail |
|--------|--------|
| Finalize manuel | Le client Portal doit appeler `batch/finalize` après legs confirmés |
| Pas de `batch-status` BFF | Pas d’endpoint FastAPI dédié ; poll swap GET |
| Rebalance bundle | Non branché UI Portal (invest seulement) |
| Flutter | Routes `/api/mobile/flutter/bundle/*` inchangées, non prioritaires |
| Image Docker stale | Rebuild API obligatoire pour LI.FI bundle |
| Python 3.9 local | Bloque pytest avec conftest / `main` |

---

## J. Invariant G (statut)

- Exposé dans réponses invest LI.FI (`_invest_via_lifi`) et **finalize** (`finalize_lifi_batch`).
- Mode **dry-run** : documenté Phase 2 backend — ne bloque pas le client.
- Validation Portal : attendre pilote post-rebuild (champ `invariant_g` dans JSON finalize).

---

## K. Prochaine étape

1. **Feu vert + rebuild** `arquantix-api` avec `BUNDLE_EXECUTION_PROVIDER=lifi_base` et mocks LI.FI.
2. **Pilote manuel Portal** (checklist §F) sur bundle TOP_5 / USDC.
3. **Phase 3** — voir `BUNDLE_RECONCILIATION_PHASE3_PRD.md`.

---

## Références

- Backend Phase 2 : `BUNDLE_EXECUTION_ADAPTER_PHASE2_LIFI_BASE.md`
- Phase 1 : `BUNDLE_EXECUTION_ADAPTER_PHASE1_REPORT.md`
- Script pilote : `services/arquantix/api/scripts/pilot_bundle_lifi_invest_mock.py`
