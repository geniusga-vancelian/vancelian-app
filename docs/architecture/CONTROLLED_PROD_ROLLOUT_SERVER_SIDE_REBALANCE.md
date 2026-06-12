# Controlled Rollout — Server-Side Portfolio Rebalancing (Privy Delegated)

| Champ | Valeur |
| --- | --- |
| **Statut** | ⏳ Prêt à piloter — flags OFF par défaut |
| **Date** | 2026-06-12 |
| **Objectif** | Un rééquilibrage de portefeuille s'exécute **100 % serveur** (chaque leg SELL/BUY signé via Privy délégué), sans navigateur |
| **Prérequis code** | Trigger `server` dans `BundleRebalanceExecutor`, driver `server_rebalance_worker.py`, sélection trigger dans le worker dépôt — ✅ mergés |
| **Références** | [SERVER_SIDE_REBALANCING_ORCHESTRATOR.md](SERVER_SIDE_REBALANCING_ORCHESTRATOR.md) · [CONTROLLED_PROD_ROLLOUT_SERVER_SIDE_SWAP_EXECUTION.md](CONTROLLED_PROD_ROLLOUT_SERVER_SIDE_SWAP_EXECUTION.md) |

---

## Principe

Le rééquilibrage **réutilise l'orchestrateur de chaînage existant** (`BundleRebalanceExecutor`) :
SELL→BUY leg par leg, idempotence par `plan_hash`, reprise, terminalisation. La seule
différence avec le flux client : **chaque leg est signé côté serveur** (trigger `server`).

```
file transaction_outbox  (un intent à la fois, sérialisé par lock_key)
  └─ bundle.v3_rebalance_requested  →  worker dépôt V3 (déjà enregistré au tick DeFi)
       └─ trigger = server  (si personne allowlistée, sinon deposit/client historique)
            └─ executor : pour chaque leg
                 quote LI.FI → signature serveur (Privy délégué)
                 → submit_signed_trade → poll + settlement (wallets, PRU/PnL, valo EUR/USDC)
            └─ leg SUBMITTED non confirmé → RUNNING → worker ré-enfile → resume au tick suivant
            └─ tous legs terminaux → COMPLETED / COMPLETED_WITH_RESIDUAL_CASH / FAILED
```

**Self-custody préservée** : signature déléguée une fois au quorum applicatif (Privy Session
Signers). Aucune clé privée détenue par Vancelian.

### Garde-fou fail-safe (zéro régression)

Si la signature serveur est impossible pour un leg, l'executor **retombe sur `expired`** pour
ce leg (jamais de signature client forcée). Au niveau cycle, le statut terminal reflète les legs
réalisés (`COMPLETED_WITH_RESIDUAL_CASH`). Avec le flag OFF / allowlist vide, le trigger reste
`deposit` (signature client historique) — **comportement inchangé**.

---

## Effet limité par allowlist (fail-closed)

```
rééquilibrage serveur(person) =
  LIFI_REBALANCE_WORKER_ENABLED = true
  ET LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS non vide
  ET email(person) ∈ allowlist
  ET wallet embedded délégué (flag Privy `delegated`)
```

Flag ON + allowlist vide → **personne** n'est rééquilibré côté serveur (tous restent client).

---

## Préconditions obligatoires (avant tout flag ON prod)

| # | Prérequis | Statut |
| --- | --- | --- |
| P1 | Exécution serveur de swap déjà pilotée OK (runbook swap, Étapes 0–4) | ⏳ |
| P2 | Secret `PRIVY_AUTHORIZATION_KEY` présent (AWS Secrets Manager) | ⏳ |
| P3 | Compte pilote a **activé l'exécution automatique** (délégation Privy `delegated=true`) | ❌ |
| P4 | Worker dépôt V3 actif (`BUNDLE_V3_DEPOSIT_FLOW`/worker) | ⏳ |
| P5 | **Go Rollout explicite** (ticket + opérateur + date) | ❌ **Non donné** |

---

## Flags production

| Variable | Valeur pilot | Effet |
| --- | --- | --- |
| `LIFI_REBALANCE_WORKER_ENABLED` | `true` | **Bascule le trigger sur `server` pour les personnes allowlistées** |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | `gaelitier@gmail.com` | Allowlist partagée |
| `PRIVY_AUTHORIZATION_KEY` | `wallet-auth:<base64>` | Clé P-256 du quorum (secret) |

> `LIFI_REBALANCE_WORKER_ENABLED` est **OFF par défaut**. Tant qu'il est OFF, tout
> rééquilibrage déclenché par dépôt utilise le trigger `deposit` (signature client), inchangé.

---

## Contraintes périmètre

| Règle | Valeur |
| --- | --- |
| Montant max par leg | **1–5 USDC** équivalent |
| Chaîne | **Base only** |
| Produit | Bundle V3 (rééquilibrage déclenché par dépôt) |
| Compte | Allowlist uniquement |

---

## Étapes de rollout (séquentielles)

### Étape 0 — Baseline (worker OFF)

- [ ] `LIFI_REBALANCE_WORKER_ENABLED=false` confirmé sur ECS prod
- [ ] Exécution serveur de swap déjà verte (runbook swap)
- [ ] **Go Étape 0**

### Étape 1 — Délégation côté compte pilote

- [ ] Le compte pilote a activé « Trading automatique » (délégation `delegated=true`)
- [ ] **Go Étape 1**

### Étape 2 — Mock / dry-run

- [ ] Smoke tests verts (§ Smoke tests)
- [ ] **Go Étape 2**

### Étape 3 — Activation (1 dépôt → rééquilibrage serveur)

```bash
LIFI_REBALANCE_WORKER_ENABLED=true
```

- [ ] Redémarrer API/worker prod
- [ ] 1 dépôt **petit montant** sur un bundle multi-actifs du compte pilote, **sans signer**
- [ ] Chaque leg → `CONFIRMED` côté serveur, cycle → `COMPLETED`
- [ ] Compta : wallets from/to impactés, PRU/PnL à jour, valo EUR/USDC figée
- [ ] Autre user → trigger reste `deposit` (allowlist)
- [ ] **Go Étape 3**

### Étape 4 — Montée progressive

- [ ] Plusieurs dépôts pilotes → rééquilibrages serveur enchaînés
- [ ] Contrôler 0 double-signature, 0 leg orpheline, 0 cycle bloqué RUNNING
- [ ] **Go Rollout complet**

---

## STOP immédiat (rollback)

| Signal | Action |
| --- | --- |
| Un **autre user** (hors allowlist) exécuté côté serveur | STOP · rollback · incident |
| Double signature / double submit d'un même leg | STOP |
| Signature serveur sur un wallet **non délégué** | STOP |
| Settlement double (débit/crédit en double) | STOP |
| Cycle bloqué RUNNING indéfiniment (legs jamais terminaux) | STOP · investiguer |

---

## Rollback

1. `LIFI_REBALANCE_WORKER_ENABLED=false`
2. Redémarrer API/worker prod
3. Les rééquilibrages repassent en trigger `deposit` (signature client)
4. (Optionnel) Le compte pilote peut **révoquer** la délégation depuis le profil

---

## Identification & vérification (prod, lecture seule)

```sql
-- cycles de rééquilibrage V3 (audit executor)
SELECT entity_id, action, metadata_->>'v3_status' AS v3_status,
       metadata_->>'trigger' AS trigger, created_at
FROM audit_events
WHERE entity_type = 'bundle_rebalance_v3'
ORDER BY created_at DESC
LIMIT 20;

-- événements de rééquilibrage en file
SELECT id, status, payload_json->>'portfolio_id' AS portfolio_id,
       payload_json->>'person_id' AS person_id, created_at
FROM transaction_outbox
WHERE event_type = 'bundle.v3_rebalance_requested'
ORDER BY created_at DESC
LIMIT 20;
```

> `trigger='server'` dans l'audit confirme que le cycle a été signé côté serveur.

---

## Smoke tests (avant Go Rollout)

```bash
cd services/arquantix/api
PYTHONPATH=. pytest \
  tests/test_rebalance_executor_server_trigger.py \
  tests/test_server_rebalance_worker.py \
  -q
```

---

## Sign-off

| Rôle | Nom | Date | Étape |
| --- | --- | --- | --- |
| Dev / Cursor | | | Trigger server + driver + sélection worker + tests + doc |
| Ops prod | | | Étapes 0–4 |
| CTO | | | Go Rollout · périmètre allowlist |
