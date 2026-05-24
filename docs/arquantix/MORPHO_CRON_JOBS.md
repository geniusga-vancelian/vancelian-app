# Morpho USDC Volt — Cron jobs

Configuration des jobs récurrents pour registry sync, réconciliation et backfill.

**Répertoire d'exécution** : `services/arquantix/web`  
**Prérequis** : `DATABASE_URL`, `.env` prod chargé, Node/pnpm disponibles.

---

## Fréquences recommandées

| Job | Commande | Fréquence | Notes |
|-----|----------|-----------|-------|
| Registry sync | `pnpm morpho:sync-vault-registry` | **Toutes les 6h** | Alimente `defi_vault_registry` depuis CMS + Morpho GraphQL |
| Réconciliation | `pnpm morpho:reconcile` | **Quotidien 06:00 UTC** | Compare ledger ↔ on-chain ; exit 1 si mismatches |
| Backfill positions | `pnpm morpho:backfill-positions` | **Manuel uniquement** | Post-migration, onboarding batch, recovery |

---

## Exemple crontab (serveur ops)

Adapter `APP_ROOT` et `LOG_DIR` :

```cron
# Morpho USDC Volt — registry sync (toutes les 6h)
0 */6 * * * cd /opt/vancelian-app/services/arquantix/web && set -a && source .env.production && set +a && /usr/bin/pnpm morpho:sync-vault-registry >> /var/log/vancelian/morpho-sync-registry.log 2>&1

# Morpho USDC Volt — réconciliation ledger (quotidien 06:00 UTC)
0 6 * * * cd /opt/vancelian-app/services/arquantix/web && set -a && source .env.production && set +a && /usr/bin/pnpm morpho:reconcile >> /var/log/vancelian/morpho-reconcile.log 2>&1
```

**Alerting** : surveiller exit code ≠ 0 (reconcile retourne 1 si mismatches/missing).

**Production ECS (recommandé)** : EventBridge Scheduler + `./scripts/vancelian-morpho-ecs-run-job.sh` — voir [MORPHO_PRODUCTION_DEPLOY_ECS.md](./MORPHO_PRODUCTION_DEPLOY_ECS.md).

---

## Exemple systemd timer (alternative)

Fichier `/etc/systemd/system/vancelian-morpho-reconcile.service` :

```ini
[Unit]
Description=Vancelian Morpho vault reconciliation

[Service]
Type=oneshot
WorkingDirectory=/opt/vancelian-app/services/arquantix/web
EnvironmentFile=/opt/vancelian-app/services/arquantix/web/.env.production
ExecStart=/usr/bin/pnpm morpho:reconcile
StandardOutput=append:/var/log/vancelian/morpho-reconcile.log
StandardError=append:/var/log/vancelian/morpho-reconcile.log
```

Fichier `/etc/systemd/system/vancelian-morpho-reconcile.timer` :

```ini
[Unit]
Description=Daily Morpho reconciliation at 06:00 UTC

[Timer]
OnCalendar=*-*-* 06:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Activer :

```bash
sudo systemctl enable --now vancelian-morpho-reconcile.timer
```

---

## Variables d'environnement cron

| Variable | Usage |
|----------|-------|
| `DATABASE_URL` | Obligatoire |
| `MORPHO_RECONCILIATION_TOLERANCE_RAW` | Tolérance match (défaut 10) |
| `PRIVY_APP_SECRET` | Requis pour réconciliation vaults `privy_earn` |
| `NEXT_PUBLIC_BASE_RPC_URL` | RPC Base pour health checks indirects |

---

## Vérification manuelle

```bash
cd services/arquantix/web
pnpm morpho:sync-vault-registry
pnpm morpho:reconcile
# Admin : /admin/morpho-vaults/monitoring → globalStatus Healthy
```

---

## Backfill (manuel)

Exécuter **une fois** après migration Phase 2 ou incident :

```bash
pnpm morpho:backfill-positions
# Option JSON :
pnpm morpho:backfill-positions -- --json
```

Ne pas planifier en cron — risque de charge GraphQL/Privy inutile.
