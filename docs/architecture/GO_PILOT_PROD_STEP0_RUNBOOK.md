# Go Pilot Prod — Étape 0 uniquement (baseline prod, flags OFF)

| Champ | Valeur |
| --- | --- |
| **Statut** | Préparation — **pas d’activation flags** |
| **Prérequis merge** | Allowlist + [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) mergés |
| **Go requis pour suite** | **Go Pilot Prod explicite** (Étapes 1–4) |

---

## Objectif Étape 0

Confirmer que la production est en **baseline safe** avant toute activation allowlist + flags orchestrateur.

**Interdit à cette étape** : activer `LIFI_INTENT_ORCHESTRATOR_ENABLED`, `LIFI_OUTBOX_WORKER_ENABLED`, `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED`, ou `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS`.

---

## Checklist opérateur

### A. ECS prod (lecture seule)

```bash
# Région us-east-1 — service arquantix-api
aws ecs describe-services \
  --region us-east-1 \
  --cluster arquantix-cluster \
  --services arquantix-api \
  --query 'services[0].taskDefinition' --output text
```

Vérifier dans la task definition : **aucune** variable suivante à `true` / non vide :

- `LIFI_INTENT_ORCHESTRATOR_ENABLED`
- `LIFI_OUTBOX_WORKER_ENABLED`
- `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED`
- `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS`

Attendu : flags absents ou `false` ; allowlist absente.

### B. Identification compte pilote (lecture seule RDS prod)

```sql
SELECT c.person_id, c.email, c.id AS client_id
FROM clients c
WHERE lower(c.email) = 'gaelitier@gmail.com';

SELECT pei.person_id, pei.external_email, pei.provider
FROM person_external_identities pei
WHERE lower(pei.external_email) = 'gaelitier@gmail.com';

SELECT id, address, chain_type, wallet_type, provider, status
FROM person_crypto_wallets
WHERE person_id = :person_id
  AND lower(provider) = 'privy'
  AND lower(wallet_type) != 'external';
```

**À documenter** : `person_id` confirmé · wallet Privy embedded Base · **un seul** email dans l’allowlist future.

### C. SQL baseline (avant pilot)

```sql
SELECT event_type, status, COUNT(*) AS n
FROM transaction_outbox
GROUP BY event_type, status;

SELECT COUNT(*) AS pe_atoms FROM pe_position_atoms;
SELECT COUNT(*) AS cost_basis FROM cost_basis_executions;

SELECT COUNT(*) AS lifi_ledger_legs
FROM person_wallet_deposits
WHERE idempotency_key LIKE 'lifi-swap:%';
```

Conserver les valeurs pour comparaison post-pilot.

### D. Smoke tests (commit déployé prod)

Sur le SHA déployé en prod (après merge allowlist, **avant** flags ON) :

```bash
cd services/arquantix/api
PYTHONPATH=. pytest tests/test_lifi_orchestrator_allowlist.py -q
PYTHONPATH=. pytest tests/test_settlement_lifi_s3b.py \
  tests/test_transaction_outbox_settlement_s3a.py \
  tests/test_settlement_contract_s2_5.py \
  tests/test_transaction_outbox_worker_s2b.py \
  tests/test_lifi_orchestrator_quote_s2a.py -q
```

Critère : **tous verts**.

### E. Swap legacy optionnel (compte pilote)

Si besoin de contrôle régression : 1 swap legacy **très petit** (≤ 1 USDC) sur `gaelitier@gmail.com` avec flags **OFF**.

Vérifier : `apply_swap_settlement` produit 1 débit + 1 crédit ; pas de `phase2_orchestrator` sur l’intent.

---

## Critère Go Étape 0

| # | Critère |
| --- | --- |
| 1 | Flags orchestrateur OFF en prod |
| 2 | Allowlist absente en prod |
| 3 | `person_id` + wallet Privy documentés |
| 4 | Baseline SQL enregistrée |
| 5 | Smoke tests verts sur commit déployé |

**Sortie Étape 0** : feu vert documenté pour demander **Go Pilot Prod Étape 1** (allowlist + orchestrateur quote seul).

---

## Verrous inchangés

- Pas Go S5 dual-run global
- Pas Go S3 Controller
- Pas élargissement allowlist avant **S4 Product Locks**
- Montants pilot futurs : **1–5 USDC**, **Base only**
