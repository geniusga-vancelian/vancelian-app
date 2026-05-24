# Privy — Go-live prod (infra + wallet client)

Runbook ops pour activer les **dépôts crypto live** crédités dans le ledger Vancelix (`person_wallet_*`).

Référence architecture : [PRIVY_IDENTITY_ARCHITECTURE.md](./PRIVY_IDENTITY_ARCHITECTURE.md).

---

## Prérequis

- Code déployé incluant migration **Alembic 158** (tables ledger + webhooks).
- Accès AWS `us-east-1` (Secrets Manager + ECS task `arquantix-api`).
- Accès dashboard Privy (App ID `cmpboubve…` ou prod équivalent).

---

## 1. Infra production (bloquant)

### 1.1 Migration 158

Au **démarrage du conteneur** ECS, `alembic upgrade head` s’exécute automatiquement (`services/arquantix/api/Dockerfile`).

**Vérification post-deploy :**

```bash
curl -s https://api.arquantix.com/api/diagnostics/db-status | jq '.alembic_version'
# Attendu : "158" (ou supérieur)
```

Tables attendues : `privy_webhook_events`, `person_wallet_deposits`, `person_wallet_balances` (+ `person_crypto_wallets` depuis 156).

### 1.2 Secrets AWS Secrets Manager

Script : `./scripts/arquantix-sync-privy-secrets.sh`

| Secret Manager | Variable ECS | Rôle |
|----------------|--------------|------|
| `arquantix/prod/privy-app-id` | `PRIVY_APP_ID` | JWT exchange, API Privy |
| `arquantix/prod/privy-jwks-url` | `PRIVY_JWKS_URL` | Vérification JWT ES256 |
| `arquantix/prod/privy-app-secret` | `PRIVY_APP_SECRET` | `GET /v1/users/{id}` — reconcile wallets |
| `arquantix/prod/privy-webhook-secret` | `PRIVY_WEBHOOK_SECRET` | Signature Svix webhooks |

```bash
PRIVY_APP_ID=... \
PRIVY_JWKS_URL=https://auth.privy.io/api/v1/apps/<APP_ID>/jwks.json \
PRIVY_APP_SECRET=... \
PRIVY_WEBHOOK_SECRET=whsec_... \
./scripts/arquantix-sync-privy-secrets.sh
```

### 1.3 Task definition ECS `arquantix-api`

Ajouter dans `secrets[]` du container (si pas déjà fait) :

```json
{ "name": "PRIVY_APP_SECRET", "valueFrom": "arn:aws:secretsmanager:us-east-1:…:secret:arquantix/prod/privy-app-secret" },
{ "name": "PRIVY_WEBHOOK_SECRET", "valueFrom": "arn:aws:secretsmanager:us-east-1:…:secret:arquantix/prod/privy-webhook-secret" }
```

Variables **plain** (environment[]) :

| Variable | Valeur prod |
|----------|-------------|
| `PRIVY_EXCHANGE_VERIFICATION_MODE` | `jwt` |
| `PRIVY_WEBHOOK_VERIFICATION_MODE` | `svix` |

**Interdit en prod :** `stub`, `PRIVY_WEBHOOK_VERIFICATION_MODE=stub`.

Redéployer le service ECS après mise à jour task definition.

### 1.4 Webhook Privy (dashboard)

| Champ | Valeur |
|-------|--------|
| URL | `https://api.arquantix.com/api/webhooks/privy` |
| Événement | `wallet.funds_deposited` |
| Secret | Copier dans `PRIVY_WEBHOOK_SECRET` (Svix) |

**Test sans signature** (route montée + secret actif) :

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.arquantix.com/api/webhooks/privy -H 'Content-Type: application/json' -d '{}'
# Attendu : 401 (signature manquante) — pas 404, pas 503 verification_not_configured
```

### 1.5 Checklist automatisée

```bash
chmod +x scripts/arquantix-privy-prod-readiness.sh
./scripts/arquantix-privy-prod-readiness.sh --api https://api.arquantix.com
```

Ou API admin :

```bash
GET /api/admin/privy-wallet/infra-readiness
```

Réponse `ready_for_live_deposits: true` + `blockers: []`.

---

## 2. Wallet client lié (bloquant)

Un dépôt on-chain n’est crédité que si l’adresse destinataire existe dans `person_crypto_wallets` pour le bon `person_id`.

### 2.1 Parcours utilisateur (prod)

1. **Login Vancelian** (SMS / passkey / portail Privy OTP).
2. **Login Privy** (OAuth ou email OTP) — crée/récupère le wallet embedded.
3. **`POST /auth/privy/link`** — lie `privy_user_id` au `person_id` du JWT Vancelian.
4. **Exchange** — `POST /auth/privy/exchange` (mobile/portail) persiste les wallets via le bridge.
5. **Reconcile admin** (si adresse absente ou drift) :

```http
POST /api/admin/privy-wallet/reconcile-wallets
{
  "person_id": "<uuid>",
  "manual_address": "0x…"   // repli si API Privy indisponible
}
```

### 2.2 Vérification par person_id

```bash
./scripts/arquantix-privy-prod-readiness.sh \
  --api https://api.arquantix.com \
  --person 8b0e0044-f1ef-47a5-99d4-370598a77492
```

Ou :

```http
GET /api/admin/privy-wallet/customer-readiness/{person_id}
```

**Critères `ready_for_live_deposit: true` :**

- `person_external_identities` (provider=`privy`) présent
- ≥ 1 wallet actif dans `person_crypto_wallets`
- Adresse EVM valide (`0x` + 40 hex)
- Infra `ready_for_live_deposits: true`

### 2.3 Compte pilote Gael (local — référence)

| Élément | Valeur |
|---------|--------|
| email | gaelitier@gmail.com |
| person_id | `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| privy_user_id | `did:privy:cmpcoqfzn001s0cjp25offnlj` |
| wallet | `0x7ae683c429ec2bc66bf1eb93713b5644dd265a44` |
| solde mock | 100 USDC (simulate-deposit local) |

Reproduire **le même état de liaison** en prod avant tout envoi live.

### 2.4 Dépôt live pilote (après 1 + 2 OK)

1. Montant minimal : **5–10 USDC**.
2. Réseau : **Ethereum mainnet** (chain_id `1`) — seul mapping ERC-20 USDC garanti aujourd’hui.
3. Adresse : celle retournée par l’app (écran Déposer) = wallet primaire admin.
4. Contrôles sous 5 min :
   - `privy_webhook_events.processing_status = processed`
   - `person_wallet_deposits` + solde mis à jour
   - Mobile / portail / Customer 360

---

## 3. Réconciliation (suite)

Plan enterprise : [PRIVY_RECONCILIATION_ENTERPRISE_PLAN.md](./PRIVY_RECONCILIATION_ENTERPRISE_PLAN.md).

**Ne pas ouvrir les dépôts live clients** tant que la réconciliation automatisée (phase 3) n’est pas en place pour la volumétrie cible — pilote interne uniquement.

---

## Rollback / incident

| Symptôme | Action |
|----------|--------|
| Webhook 503 `verification_not_configured` | Injecter `PRIVY_WEBHOOK_SECRET`, redémarrer ECS |
| Dépôt on-chain OK, ledger vide | Vérifier wallet address = `person_crypto_wallets` ; replay manuel via admin simulate (staging) ou correction adresse |
| `privy_webhook_events` en `failed` | Logs CloudWatch `/ecs/arquantix-api` ; corriger mapping asset/chain |

---

## Fichiers associés

| Fichier | Rôle |
|---------|------|
| `scripts/arquantix-sync-privy-secrets.sh` | Sync Secrets Manager |
| `scripts/arquantix-privy-prod-readiness.sh` | Sonde infra + client |
| `api/services/privy_wallet/readiness.py` | Logique checklist |
| `api/services/privy_wallet/webhook_router.py` | Endpoint webhook |
