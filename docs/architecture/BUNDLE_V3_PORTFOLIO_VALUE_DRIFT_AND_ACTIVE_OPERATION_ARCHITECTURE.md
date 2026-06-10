# Architecture — Drift NAV totale (`portfolio_value`) + reprise worker UI

| Champ | Valeur |
| --- | --- |
| **Statut** | Document d’architecture backend + portail (prod) |
| **Date** | 2026-06-10 |
| **Audience** | Backend, frontend portail, SRE, produit technique |
| **Prérequis** | [`BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md`](BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md) · [`BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md`](BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md) |
| **Incident résolu** | Kings — plan partiel (~3,6 USDC ETH) avec cash leg ~6,4 USDC ; worker invisible au refresh page bundle |

---

## 1. Problème et décision

### 1.1 Erreur de modèle : deux bases de calcul parallèles

Le drift engine calculait `portfolio_value_usdc = spot + cash_leg` pour l’affichage, mais les **poids et deltas** sur `invested_value_usdc` seul (`weight_basis = invested_assets`).

Conséquences (Kings, NAV ~18,36 USDC, cash ~6,38 USDC) :

| Base | BTC | ETH | Plan typique |
| --- | --- | --- | --- |
| Investi seul (11,98 USDC) | Surpondéré 100 % vs 70 % | Sous-pondéré 0 % vs 30 % | Achat ETH ~3,59 USDC |
| **NAV totale (18,36 USDC)** | ~65 % vs 70 % (léger sous-poids) | 0 % vs 30 % | Achat ETH ~**5,51 USDC** |

Le mode planner `portfolio_value_cash_deploy` (si `cash > invested`) recalculait correctement la NAV, mais **ne s’activait pas** quand `cash < invested` — cas fréquent après premiers legs ou alignement pilote.

### 1.2 Décision architecture (PR-2.1)

**Une seule base métier** : `weight_basis = portfolio_value`.

```
target_value_usdc(asset) = portfolio_value_usdc × target_weight_bps / 10_000
current_weight_bps(asset)  = current_value_usdc(asset) / portfolio_value_usdc × 10_000
drift_bps                  = current_weight_bps − target_weight_bps
```

Doctrine :

- Le **cash leg USDC** fait partie de la **NAV** du bundle (balance totale).
- Le cash leg **n’est pas** une allocation cible (poids visé → 0 % en régime permanent).
- Le cash leg **finance** les achats (`cash_funding_source = separate`) sans être exclu du dénominateur drift.

Le planner expose un mode unique : `planning_mode = portfolio_drift`.  
Le chemin `portfolio_value_cash_deploy` (seuil `CASH_DOMINANT_INVESTED_RATIO`) est **retiré** — redondant une fois le drift aligné sur la NAV.

### 1.3 Reprise worker au chargement page bundle

Un dépôt V3 ou un rééquilibrage manuel laisse souvent `v3_status = RUNNING` (legs en attente signature Privy).  
Sans reprise UI, un refresh de la page bundle **perdait** le contexte d’exécution.

**Décision** : endpoint read-only `GET /bundle/{portfolio_id}/active-operation` + panneau portail `PortalLazyBundleActiveOperation` (même stepper que l’invest, Web3 lazy, polling 4 s, chaîne `resume` + `executeBundleTrade`).

---

## 2. Composants backend

### 2.1 `drift_engine.py`

| Champ snapshot | Rôle |
| --- | --- |
| `portfolio_value_usdc` | `invested_value_usdc + cash_value_usdc` |
| `invested_value_usdc` | Spot bundle uniquement (inchangé) |
| `cash_value_usdc` | Cash leg PE |
| `weight_basis` | **`portfolio_value`** (remplace `invested_assets`) |

`compute_bundle_drift_snapshot` reste **read-only** (aucune écriture PE / swap).

### 2.2 `rebalance_planner.py`

Entrée : snapshot drift. Sortie : `sell_plan`, `buy_plan`, `plan_hash`, `planning_mode: portfolio_drift`.

Règles inchangées côté exécution :

- `MIN_REBALANCE_DELTA_USDC` (défaut 1 USDC)
- `MIN_DRIFT_BPS` (défaut 200)
- Sell puis buy ; cash leg = financement

### 2.3 `rebalancing_portfolio.py` — `get_active_bundle_operation`

Priorité de détection :

1. `find_running_v3_rebalance_execution(portfolio_id)` → `v3_status = RUNNING`, `asset_lines` fusion plan + résultats partiels.
2. Sinon lock invest actif sur batch V3 deposit → `v3_status = QUEUED`.
3. Sinon `status: none`.

Réponse type (RUNNING) :

```json
{
  "status": "active",
  "operation_type": "v3_deposit_rebalance | portfolio_rebalancing",
  "portfolio_id": "…",
  "v3_status": "RUNNING",
  "rebalance_execution_id": "…",
  "trigger": "deposit | manual",
  "asset_lines": [{ "asset": "ETH", "action": "buy", "status": "pending", … }],
  "sell_results": [],
  "buy_results": []
}
```

Route mobile : `GET /api/app/bundle/{portfolio_id}/active-operation` (`test_clients/router.py`).

### 2.4 API portail (BFF)

`GET /api/portal/bundles/active-operation/{portfolioId}` → proxy upstream avec session portail.

---

## 3. Composants frontend (portail)

| Module | Rôle |
| --- | --- |
| `PortalLazyBundleActiveOperation` | Dynamic import + `PortalWeb3BoundaryLazy` (perf R4.5-F5-B) |
| `PortalBundleActiveOperationPanel` | Poll active-operation · `TransactionProcessingPage` · reprise legs |
| `bundleActiveOperationResume.ts` | Chaîne sign → submit → poll → resume (hors hook invest) |
| `bundleSteps.ts` | `buildBundleActiveOperationSteps`, `isTerminalBundleV3Status` |

Intégration : `PortalCryptoWalletBundleDetailScreen` — section au-dessus du panneau allocation read-only.

Comportement :

- Au **mount** et toutes les **4 s** si opération active non terminale.
- Si legs `pending` + `swap_id` → reprise automatique signature LI.FI.
- Terminal (`COMPLETED`, `COMPLETED_WITH_RESIDUAL_CASH`, `FAILED`, `NO_ACTION`) → masque le panneau, invalide cache wallet.

---

## 4. Cas de validation prod (Kings)

Snapshot attendu après correctif (ordre de grandeur) :

| Métrique | Valeur |
| --- | --- |
| Investi | ~11,98 USDC |
| Cash leg | ~6,38 USDC |
| NAV | ~18,36 USDC |
| Achat ETH planifié | ~**5,51 USDC** (pas ~3,59) |
| Reliquat cash post-leg | ~0,87 USDC (delta BTC < 1 USDC min) |

Scripts audit :

```bash
./scripts/arquantix-ecs-bundle-drift-engine-audit.sh
```

---

## 5. Tests automatisés

| Fichier | Cas clé |
| --- | --- |
| `test_bundle_drift_engine.py` | `weight_basis == portfolio_value` · golden sans cash inchangé |
| `test_bundle_rebalance_planner.py` | `test_kings_partial_cash_deploys_eth_on_portfolio_nav` · Majors full spot |
| `test_bundle_rebalance_planner.py` | `test_kings_cash_dominant_deploys_portfolio_value_targets` · cash >> investi |

---

## 6. Déploiement

| Surface | Workflow GHA (push `main`) |
| --- | --- |
| API FastAPI | `arquantix-api-deploy.yml` (`services/arquantix/api/**`) |
| Portail Next | `vancelian-next-deploy.yml` (`services/arquantix/web/**`) |

Aucun flag env supplémentaire. Comportement effectif dès rollout ECS des deux services.

---

## 7. Évolutions connues (hors scope)

- Absorption du reliquat cash < `MIN_REBALANCE_DELTA_USDC` sur le dernier leg.
- `plan_hash_changed` après leg terminé — nouvelle exécution explicite vs resume figé.
- Mise à jour PRD § weight_basis (`BUNDLE_REBALANCING_ENGINE_V3_PRD.md` § PR-2).
