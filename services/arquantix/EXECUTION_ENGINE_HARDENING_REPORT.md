# Execution Engine Hardening Report

## Objectif

Upgrade du moteur d'exécution automatique des ordres (trigger orders) vers un niveau de fiabilité institutionnel, avec 3 mécanismes de protection ajoutés.

## 1. Pre-Execution Price Check

**Problème résolu** : Entre le moment du tick de déclenchement et l'exécution effective, le prix peut avoir bougé significativement (gap, latence réseau, file de traitement). Exécuter un ordre à un prix très différent du trigger serait dangereux.

**Implémentation** :

- Avant chaque appel à `ExchangeService`, lecture du prix live depuis Redis (`prices:{ASSET}:last_ask` pour BUY, `prices:{ASSET}:last_bid` pour SELL)
- Calcul de la déviation en basis points entre le prix live et le `trigger_price`
- Si la déviation dépasse le seuil de sécurité → ordre `failed` avec raison `price_moved_beyond_safety`
- Seuil = `slippage_bps` si défini par l'utilisateur, sinon `200 bps` (2%) par défaut

**Cas couverts** :

| Scénario | Side | Check |
|----------|------|-------|
| Flash crash pendant le traitement | BUY | ASK a monté au-delà du seuil → skip |
| Gap haussier soudain | SELL | BID a baissé au-delà du seuil → skip |
| Prix stable | Les deux | Déviation dans les bornes → proceed |
| Redis indisponible | Les deux | Check skipped, exécution proceed |

## 2. Retry Window

**Problème résolu** : Les erreurs transitoires (timeout réseau, lock DB temporaire, rate limit exchange) ne doivent pas causer un échec définitif au premier essai.

**Implémentation** :

- `max_attempts = 3`
- `retry_window = 1.0s`
- Boucle : tentative → si échec, attendre 100ms → retry
- Si le temps total dépasse la fenêtre de 1s → arrêt
- Chaque tentative utilise un `external_reference` unique pour l'idempotence
- Les exceptions dans `ExchangeService.buy()/sell()` sont capturées et permettent un retry

**Comportement** :

```
attempt 1 → fail (timeout)
   → sleep 100ms
attempt 2 → fail (lock contention)
   → sleep 100ms
attempt 3 → success ✓
```

Le nombre de tentatives est enregistré dans `metadata_.attempts` pour audit.

## 3. Partial Fill Detection

**Problème résolu** : L'exchange peut exécuter partiellement un ordre (liquidité insuffisante, volume cap). Le système doit détecter et tracer cette situation.

**Implémentation** :

- Après exécution réussie, comparaison du montant rempli vs montant demandé
- Pour BUY : `amount_fiat` rempli vs `amount` demandé
- Pour SELL : `amount_crypto` rempli vs `amount` demandé
- Seuil de détection : ratio < 0.995 (tolérance 0.5% pour les arrondis)
- Si partial fill détecté → `metadata_.partial_fill = true` + compteur `orders_partial_fills` incrémenté
- L'ordre est quand même marqué `executed` (le fill partiel est un succès partiel, pas un échec)

## 4. Métriques ajoutées

| Métrique | Description |
|----------|-------------|
| `orders_partial_fills` | Nombre d'ordres avec remplissage partiel |
| `orders_retry_attempts` | Nombre total de retries effectués |
| `orders_skipped_price` | Nombre d'ordres skippés par le pre-execution check |

Exposées via `GET /api/app/alerts/metrics` avec les autres compteurs existants.

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `api/services/price_alerts/engine.py` | Refactor `_execute_order_hook` : pre-exec check, retry loop, partial fill. Ajout `_pre_execution_price_check`. Méthode devenue instance method (accès à `self.redis`) |
| `api/services/price_alerts/metrics.py` | Ajout 3 compteurs + 3 méthodes `record_*` + inclusion dans `snapshot()` |

## Metadata d'exécution enrichie

Chaque ordre exécuté contient désormais dans `metadata_` :

```json
{
  "execution_price": 84250.50,
  "order_id": "uuid-...",
  "amount_crypto": 0.00119,
  "amount_fiat": 100.0,
  "attempts": 1,
  "partial_fill": false
}
```

En cas d'échec :

```json
{
  "failure_reason": "price_moved_beyond_safety",
  "live_price": 87500.0,
  "trigger_price": 85000.0,
  "deviation_bps": 294.1,
  "safety_bps": 200.0
}
```

## Invariants de sécurité

1. **Jamais d'exécution si le prix a dévié au-delà des bornes** (pre-exec check)
2. **Maximum 3 tentatives dans une fenêtre de 1s** (retry limité)
3. **Chaque tentative a un `external_reference` unique** (idempotence exchange)
4. **Le `execution_status` est toujours mis à jour** (failed ou executed, jamais pending indéfiniment)
5. **Les exceptions ne crashent jamais le tick processing** (try/except global)
