# Ledgity Vaults — Cron jobs

Configuration du job de réconciliation ledger ↔ lyToken on-chain.

**Répertoire d'exécution** : `services/arquantix/web`  
**Prérequis** : `DATABASE_URL`, `.env` prod chargé, Node/pnpm disponibles.

---

## Fréquences recommandées

| Job | Commande | Fréquence | Notes |
|-----|----------|-----------|-------|
| Réconciliation | `pnpm ledgity:reconcile` | **Quotidien 06:15 UTC** | Compare ledger ↔ on-chain ; exit 1 si mismatches / PPS indispo / liquidité |
| Réconciliation post-tests | `pnpm ledgity:reconcile` | **Après chaque batch live** | Manuel ou CI post-déploiement beta |

---

## Exemple crontab (serveur ops)

Adapter `APP_ROOT` et `LOG_DIR` :

```cron
# Ledgity vaults — réconciliation ledger (quotidien 06:15 UTC)
15 6 * * * cd /opt/vancelian-app/services/arquantix/web && set -a && source .env.production && set +a && /usr/bin/pnpm ledgity:reconcile >> /var/log/vancelian/ledgity-reconcile.log 2>&1
```

**Alerting** : surveiller exit code ≠ 0 (reconcile retourne 1 si mismatches, missing, `pps_unavailable` ou `liquidity_warning`).

Voir aussi : [LEDGITY_PRODUCTION_CHECKLIST.md](./LEDGITY_PRODUCTION_CHECKLIST.md)

---

## Vérification manuelle

```bash
cd services/arquantix/web
pnpm ledgity:reconcile
# ou JSON :
pnpm ledgity:reconcile -- --json
```

Monitoring admin : `/admin/ledgity-vaults/monitoring`
