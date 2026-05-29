# Cost Basis V2 — Checklist de déploiement production

**Date :** 2026-05-29  
**Décision produit :** déployer Cost Basis V2 — **stop feature development** sur ce périmètre.  
**Phase suivante (séparée) :** Morpho / Ledgity / `vault_positions` / `liabilities` / `yield_events` — **hors ce déploiement**.

**Références :**

- [COST_BASIS_V2_DOCTRINE.md](./COST_BASIS_V2_DOCTRINE.md) — règles normatives
- [COST_BASIS_V2_IMPLEMENTATION_REPORT.md](./COST_BASIS_V2_IMPLEMENTATION_REPORT.md) — implémentation
- [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md) — Compose / `DATABASE_URL` / doctor

---

## 0. Périmètre gelé (complet)

| Inclus | Exclu de cette phase |
| --- | --- |
| Doctrine clarifiée | Morpho / Ledgity ingestion |
| `cost_basis_executions` (trades / swaps / rebalance / liquidation) | `vault_positions`, `position_movements` |
| Self-trading, Li.FI, exchange, bundle scoped | `liabilities`, `yield_events` |
| Backfills Li.FI + bundle (CLI) | PRU inventé sur dépôt vault |
| Charts `wallet_history` depuis exécutions si présentes | |
| UI : `—` si PRU null (plus de `$0.000000`) | |

**Aucune nouvelle feature** à merger avant ce déploiement.

---

## 1. Validation pré-déploiement (exécutée 2026-05-29)

### 1.1 Tests backend — périmètre Cost Basis V2

Commande (depuis `services/arquantix/api`) :

```bash
python3 -m pytest \
  tests/test_cost_basis_v2.py \
  tests/test_cost_basis_lifi_backfill.py \
  tests/test_cost_basis_bundle.py \
  tests/test_wallet_statistics.py \
  tests/test_wallet_history.py \
  tests/test_bundle_lifi_phase2.py \
  tests/test_bundle_cost_basis.py \
  -q
```

**Résultat :** **42 passed** (0 failed).

### 1.2 Tests backend — périmètre élargi (settlement / isolation)

Même répertoire, fichiers additionnels :

```bash
python3 -m pytest \
  tests/test_lifi_swap_settlement.py \
  tests/test_lifi_actual_receive_settlement.py \
  tests/test_bundle_self_trading_isolation.py \
  -q
```

**Résultat :** **6 failed**, **59 passed**.

**Analyse des échecs :** non liés à Cost Basis V2 — `PrivyWalletNotFoundError` dans les fixtures Privy (`simulate_deposit` / wallet introuvable). Échecs **pré-existants ou environnement de test**, pas de régression sur `ingest_lifi` / `cost_basis_executions`.

**Recommandation prod :** ne pas bloquer le déploiement V2 sur ces tests ; traiter les fixtures Privy en tâche séparée si besoin.

### 1.3 Import / démarrage API (sans DB live)

```bash
cd services/arquantix/api
python3 -c "from main import app; from services.cost_basis.models import CostBasisExecution; print('OK', app.title)"
```

**Résultat :** `API imports OK Arquantix API`.

### 1.4 Frontend

```bash
cd services/arquantix/web
npx tsc --noEmit
```

**Résultat (2026-05-29) :** échecs **Prisma client non généré** (`@prisma/client` exports manquants) — **pré-existant**, pas spécifique Cost Basis.

**Fichier UI touché par V2 :** `src/components/portal/markets/PortalInstrumentHoldingCard.tsx` (affichage PRU `—` si null).

**Checklist CI / prod web :**

```bash
cd services/arquantix/web
npm run db:generate   # ou prisma generate
npm run build         # gate recommandé avant deploy Next
```

### 1.5 Migration Alembic — seule migration V2

| Vérification | Résultat |
| --- | --- |
| Révision head | `170` (`alembic heads` → `170 (head)`) |
| Fichier | `alembic/versions/170_cost_basis_executions.py` |
| `down_revision` | `169` |
| Autre migration `cost_basis_executions` | **Aucune** |

**Note :** d’anciennes colonnes `cost_basis` / `cost_basis_consumed` sur d’**autres** tables (PE atoms, exchange_orders) existent déjà — **sans lien** avec la table V2.

**Upgrade :** création additive de `public.cost_basis_executions` + index + contrainte unique `(provider_source, provider_execution_id)`.

**Downgrade :** `DROP TABLE cost_basis_executions` — **destructif pour les lignes ingérées** ; à éviter en prod sauf rollback planifié (§6).

---

## 2. Prérequis production

- [ ] Branche / image API contenant Cost Basis V2 **mergée** et taguée
- [ ] Image ou artefact **web** avec `PortalInstrumentHoldingCard` à jour
- [ ] **`DATABASE_URL`** prod identique entre conteneur API, job Alembic, scripts backfill
- [ ] Backup DB récent (ou snapshot) — **obligatoire** avant `upgrade head`
- [ ] Fenêtre de maintenance courte (migration + restart API + dry-run backfill)
- [ ] Accès shell conteneur `arquantix-api` ou équivalent prod
- [ ] **Validation explicite** opérateur sur `.env` / Compose — **ne pas** changer `COMPOSE_PROJECT_NAME` / `DB_NAME` dans le cadre de ce déploiement

---

## 3. Commandes production (ordre strict)

Remplacer `<COMPOSE_PROJECT>`, chemins compose et noms de service selon l’environnement prod (voir runbook). Exemple pattern :

```bash
# Depuis la racine du dépôt
export COMPOSE_PROJECT="$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)"
export COMPOSE_FILE="${ARQUANTIX_COMPOSE_FILE:-docker-compose.arquantix-recovery.yml}"
```

### 3.1 Vérifier révision actuelle

```bash
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-api alembic current
```

Attendu **avant** deploy : `169` (ou inférieur si retard). **Après** : `170`.

### 3.2 Appliquer la migration

```bash
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-api alembic upgrade head
```

**Vérification :**

```bash
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-api alembic current
# → 170 (head)

docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-db psql -U arquantix -d <DB_NAME> -c "\d public.cost_basis_executions"
```

### 3.3 Déployer / redémarrer l’API

```bash
# Selon votre pipeline : pull image + recreate, ou :
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  up -d --no-deps arquantix-api
```

**Smoke HTTP (adapter host / token) :**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://<API_HOST>/health
# ou endpoint interne équivalent
```

**Logs au démarrage :** pas d’`ImportError` sur `services.cost_basis`, pas d’erreur SQL sur ORM `CostBasisExecution`.

### 3.4 Déployer le web (si séparé)

Rebuild / redeploy Next.js avec le commit UI. Pas de migration Prisma liée à V2.

### 3.5 Backfill Li.FI — dry-run obligatoire

Dans le conteneur API (ou host avec `DATABASE_URL` prod) :

```bash
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-api python3 -m scripts.backfill_cost_basis_lifi --dry-run -v
```

Filtres recommandés pour premier passage :

```bash
# Par actif concerné (ex. AAVE)
python3 -m scripts.backfill_cost_basis_lifi --dry-run --asset AAVE -v

# Ou par client
python3 -m scripts.backfill_cost_basis_lifi --dry-run --client-id <PE_CLIENT_UUID> -v
```

**Valider le JSON :**

- `errors` = 0
- `eligible` cohérent avec swaps CONFIRMED self-trading attendus
- `ignored` / `bundle_internal` attendus pour legs bundle
- Montants `amount_out` / `amount_out_source` plausibles

### 3.6 Backfill Li.FI — execute (après validation dry-run)

```bash
docker compose --project-name "$COMPOSE_PROJECT" --env-file .env.arquantix -f "$COMPOSE_FILE" \
  exec arquantix-api python3 -m scripts.backfill_cost_basis_lifi --execute --asset AAVE -v
```

**Idempotent :** relancer ne duplique pas (`uq_cost_basis_executions_provider`).

**Option prod prudente :** `--allow-onchain-resolve` uniquement si audit/ledger insuffisants (charge RPC).

### 3.7 Backfill bundle (optionnel)

Si des bundles Li.FI confirmés existent en prod :

```bash
python3 -m scripts.backfill_cost_basis_bundle_lifi --dry-run -v
python3 -m scripts.backfill_cost_basis_bundle_lifi --execute --portfolio-id <PORTFOLIO_UUID> -v
```

Sinon : les **nouveaux** legs alimentent via hook `bundle_lifi_leg_service` ; lazy backfill au premier `build_wallet_statistics` bundle (max 200 swaps).

---

## 4. Vérifications post-déploiement

| # | Check | Critère de succès |
| --- | --- | --- |
| 1 | Migration | `alembic current` = `170` |
| 2 | Table | `SELECT COUNT(*) FROM cost_basis_executions` ≥ 0 ; pas d’erreur |
| 3 | Nouveau swap Li.FI | Après CONFIRMED, lignes `provider_source=lifi` pour scope direct |
| 4 | PRU UI | Actif Li.FI historique : `avg_buy_price_*` non null après backfill ; UI `—` → valeur |
| 5 | Exchange legacy | BUY/SEUR existant : PRU via lazy backfill `exchange` au chargement stats |
| 6 | Bundle | PRU actif dans bundle ≠ PRU direct si scopes différents |
| 7 | Charts | `GET .../wallet/history?mode=performance_value` points non vides si exécutions présentes |
| 8 | Vault | Dépôt Morpho **ne crée pas** de ligne `cost_basis_executions` (doctrine) |

**Endpoints de contrôle (avec auth app client) :**

- `GET /api/app/crypto-positions/{asset}`
- `GET /api/app/wallet/statistics/{asset}`
- `GET /api/app/bundle/{portfolio_id}/history?mode=performance_value`

---

## 5. Revue des risques

| Risque | Sévérité | Mitigation |
| --- | --- | --- |
| Migration 170 non appliquée | **Bloquant** | `alembic current` + `\d cost_basis_executions` avant trafic |
| `DATABASE_URL` divergent (script vs API) | **Critique** | Doctor / même `DB_NAME` partout |
| Double comptage ingestion | Faible | Contrainte unique provider |
| PRU null jusqu’au backfill | **Attendu** | Dry-run puis `--execute` ; nouveaux swaps auto |
| Écart taille position Privy vs `crypto_positions` | Moyen | Documenté audit §8.4 — hors scope V2 |
| Backfill `amount_out` manquant | Moyen | Dry-run ; `--allow-onchain-resolve` en dernier recours |
| Ingestion bundle échoue silencieusement | Faible | Log `bundle_lifi cost_basis ingest failed` ; backfill CLI |
| Downgrade Alembic | **Élevé** | Supprime la table — éviter (§6) |

**Données additives uniquement :** aucune suppression ni modification des `exchange_orders`, swaps, ledger existants.

---

## 6. Plan de rollback

### 6.1 Désactiver l’usage fonctionnel (sans toucher la DB)

1. **Redéployer l’API** sur l’image / commit **précédent** Cost Basis V2 (avant hooks `ingest_lifi`, `ingest_exchange`, refactor `wallet_statistics` / `wallet_history`).
2. Le PRU redevient calculé depuis `exchange_orders` uniquement (comportement legacy).
3. La table `cost_basis_executions` **reste** en base (orpheline) — **sans impact** si l’ancien code ne la lit pas.

**Pas de feature flag** en V2 — rollback = **revert déploiement API**.

### 6.2 État des données

| Objet | Rollback safe ? |
| --- | --- |
| `cost_basis_executions` (lignes) | Additives — peuvent rester |
| `exchange_orders` | Inchangées |
| `person_wallet_swaps` | Inchangées |
| Migration 170 appliquée | Table vide ou avec données — OK pour ancien code |

### 6.3 Rollback migration (déconseillé)

```bash
alembic downgrade 169
```

**Effet :** `DROP TABLE public.cost_basis_executions` — **perte des PRU ingérés**. À réserver à incident schéma, pas à simple revert fonctionnel.

### 6.4 Web

Revert `PortalInstrumentHoldingCard.tsx` si besoin (affichage `$0.000000` legacy) — indépendant de l’API.

---

## 7. Sign-off

| Rôle | Nom | Date | OK |
| --- | --- | --- | --- |
| Tech / API | | | ☐ |
| Ops / DB | | | ☐ |
| Produit | | | ☐ |

**Critères de GO :**

- [ ] Tests §1.1 verts
- [ ] Migration 170 validée sur staging
- [ ] Dry-run backfill Li.FI prod validé (`errors=0`)
- [ ] Backup DB
- [ ] Morpho/Ledgity **explicitement hors scope** ce déploiement

---

## 8. Phase suivante (ne pas mélanger)

**Cost Basis — Vault / DeFi custody** (nouvelle phase) :

- `vault_positions`, `position_movements`, `liabilities`, `yield_events`
- Charts épargne NAV / yield
- Doctrine : [COST_BASIS_V2_DOCTRINE.md](./COST_BASIS_V2_DOCTRINE.md) §5–8

---

*Checklist générée pour déploiement contrôlé — aucune implémentation additionnelle requise dans cette phase.*
