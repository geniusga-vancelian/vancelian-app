# M1 Bars Purge Implementation Report

## Executive Summary

Purge automatique des chandelles 1m implémentée et testée. Les barres de plus de 24 heures sont supprimées toutes les 12 heures par un thread daemon. Aucune régression sur les 36 tests core.

## Files Created

| Fichier | Rôle |
|---------|------|
| `api/services/market_data/purge_m1_bars.py` | Service de purge : `run_purge_m1_bars(session)` — supprime les lignes `open_time < now - 24h` via SQL direct |
| `api/tests/test_purge_m1_bars.py` | 3 tests : suppression des anciennes, table vide, conservation des récentes |

## Files Modified

| Fichier | Modification |
|---------|-------------|
| `api/main.py` | Ajout d'un thread daemon `_cron_purge_m1_loop` (intervalle 12h) qui appelle `run_purge_m1_bars` |

## Scheduler Integration

Le scheduler existant dans `main.py` lance deux threads daemon au démarrage :

1. **Cron Refresh Data** (existant) — toutes les 60 secondes, backfill des barres en retard
2. **Cron Purge M1 bars** (nouveau) — toutes les 12 heures, purge des barres 1m > 24h

Le job de purge :
- Importe `SessionLocal` et `run_purge_m1_bars` à l'intérieur du thread (lazy import)
- Ouvre une session, exécute la purge, ferme la session
- Logge via `add_cron_log` (visible dans l'admin `/api/market-data/cron-refresh-logs`)
- Gère les exceptions sans crasher le thread

## Retention Policy (24h)

| Paramètre | Valeur |
|-----------|--------|
| Rétention | 24 heures |
| Fréquence de purge | 12 heures |
| Table concernée | `market_data_bars_1m` uniquement |
| Tables non touchées | `bars_5m`, `bars_1h`, `bars_4h`, `bars_1d`, `bars_1w` |

La fenêtre utile pour le wallet history est 0–2h (granularité 1m). La rétention de 24h offre une marge confortable.

## Performance Notes

- **Requête** : `DELETE FROM public.market_data_bars_1m WHERE open_time < :cutoff` — SQL direct via `text()`
- **Index** : `ix_market_data_bars_1m_open_time` existe déjà (migration 065) — le DELETE utilise un index scan
- **Volume estimé** : ~6 instruments × 1440 candles/jour = ~8 640 lignes supprimées par purge (négligeable)
- **Impact** : aucun lock bloquant, exécution < 100ms attendue

## Test Results

| Test | Description | Résultat |
|------|-------------|----------|
| `test_purge_deletes_old_keeps_recent` | Insère 1 bar à -48h et 1 à -1h, purge, vérifie que seule la récente reste | PASS |
| `test_purge_empty_table` | Purge sur table vide retourne 0 sans erreur | PASS |
| `test_purge_does_not_touch_recent` | 5 bars récentes (< 5min), purge en supprime 0 | PASS |

**Régression** : 36 tests core passent (purge + wallet_history + exchange).

## Final Status

- Purge toutes les 12h : **OUI**
- Rétention 24h : **OUI**
- Aucune régression : **OUI**
- Tables 5m/1h/4h/1d non impactées : **OUI**
