# Market data — worker Binance WebSocket (production)

**Cible :** cotations live `BTCUSDT`, `ETHUSDT`, etc. dans `market_data_latest_quotes`.  
**Service ECS :** `arquantix-market-ws` (singleton, `desiredCount=1`).  
**Image :** même ECR que `arquantix-api` (`arquantix-api:<git-sha>`).  
**Commande :** `python3 scripts/run_binance_ws_ingestion.py` (pas d’`uvicorn`, pas d’`alembic`).

Documents liés :

| Document | Rôle |
| --- | --- |
| [`CI_DEPLOY_MATRIX.md`](CI_DEPLOY_MATRIX.md) | Workflows deploy API + worker |
| `services/arquantix/api/scripts/README_MARKET_DATA_SETUP.md` | Setup local |
| `services/arquantix/docs/audit/MARKET_DATA_STEP9_IMPLEMENTED.md` | Implémentation WS |

---

## Architecture

| Composant | Rôle |
| --- | --- |
| **arquantix-market-ws** | Connexion `wss://stream.binance.com` (bookTicker), upsert quotes + alertes prix |
| **arquantix-api** | REST `/api/market-data/*`, WS `/ws/market-data` (lit la DB), cron **barres OHLC** uniquement |
| **Binance REST fallback** | `market_summary_repo` si quote > 60 s (requêtes HTTP ponctuelles) |

Le cron admin « Refresh Data » (`/admin/crypto-market`) ne remplace **pas** ce worker.

---

## Déploiement (CI)

Push `main` sur `services/arquantix/api/**` → workflow **Arquantix API (FastAPI)** :

1. Build & push image `arquantix-api:<sha>`
2. Deploy `arquantix-api`
3. Deploy `arquantix-market-ws` (même tag)

Premier provision manuel (une fois par compte AWS) :

```bash
./scripts/arquantix-provision-market-ws-service.sh
```

---

## Vérification prod

```bash
./scripts/arquantix-verify-market-quotes-prod.sh
```

Attendu : écart API vs Binance **< 2 %** sur `BTCUSDT` / `ETHUSDT`.

Logs CloudWatch : `/ecs/arquantix-market-ws` — chercher `Loaded N Binance instrument(s)` et commits réguliers.

```bash
aws logs tail /ecs/arquantix-market-ws --region us-east-1 --follow
```

État ECS :

```bash
aws ecs describe-services --region us-east-1 --cluster arquantix-cluster \
  --services arquantix-market-ws \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount,task:taskDefinition}'
```

---

## Secours REST (one-shot)

Si le worker WS est arrêté, rafraîchir une fois toutes les quotes Binance :

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 scripts/run_binance_ingestion.py'
```

Puis redémarrer le worker :

```bash
./scripts/arquantix-provision-market-ws-service.sh
```

---

## Variables d’environnement

Héritées de la task `arquantix-api` (clone à l’enregistrement), avec override prod US :

| Variable | Obligatoire | Prod ECS (us-east-1) |
| --- | --- | --- |
| `DATABASE_URL` | Oui | Identique API |
| `REDIS_URL` | Oui (PriceAlertEngine) | Identique API |
| `BINANCE_REST_BASE_URL` | Recommandé | `https://data-api.binance.vision` |
| `BINANCE_WS_BASE_URL` | Recommandé | `wss://data-stream.binance.vision` |
| `BINANCE_USE_VISION_ENDPOINTS` | Optionnel | `true` (défauts code après deploy) |

`api.binance.com` / `stream.binance.com` renvoient souvent **451** depuis AWS US — ne pas utiliser en prod sans test.

**API** : même variables sur `arquantix-api` (fallback REST market-summary) :

```bash
./scripts/arquantix-sync-api-binance-vision-env-prod.sh
```

---

## Dépannage

| Symptôme | Cause probable | Action |
| --- | --- | --- |
| Prix figés, drift > 5 % | Worker arrêté ou 0 instrument actif | `provision-market-ws-service.sh`, vérifier logs |
| Task exit 0 immédiat | Aucun instrument `provider=binance` en DB | `run_binance_ingestion` + `ensure_binance_instruments` via RunTask API |
| Reconnect loop | Réseau / Binance | Logs `reconnect`; vérifier sortie Internet SG |
| Service MISSING | Jamais provisionné | `./scripts/arquantix-provision-market-ws-service.sh` |

---

## Backup REST planifié (optionnel)

Pas de scheduler intégré. Recommandation ops : EventBridge `rate(10 minutes)` → RunTask `run_binance_ingestion.py` (même pattern que `run_defi_observability_tick_prod.sh --ecs-once`). Le worker WS reste la source temps réel.
