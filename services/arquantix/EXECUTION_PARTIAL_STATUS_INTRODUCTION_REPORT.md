# Execution Partial Status Introduction Report

## Objectif

Introduire un statut d'exécution explicite `"partial"` dans le moteur d'exécution automatique des ordres, afin de distinguer clairement les fills complets des fills partiels au niveau backend, API et UI.

## Avant / Après

### Avant

| execution_status | Signification |
|------------------|---------------|
| `pending` | En attente de déclenchement |
| `executed` | Exécuté (complet ou partiel, indistinct) |
| `failed` | Échec |

Un fill partiel était marqué `"executed"` avec un simple flag `metadata_.partial_fill = true`. Il n'y avait pas de distinction visible dans l'API ni dans l'UI.

### Après

| execution_status | Signification |
|------------------|---------------|
| `pending` | En attente de déclenchement |
| `executed` | Exécuté intégralement (fill >= 99.5%) |
| `partial` | Exécuté partiellement (0 < fill < 99.5%) |
| `failed` | Échec (y compris zero-fill) |

## Migration

**Aucune migration nécessaire.** Le champ `execution_status` est un `String(20)` libre en PostgreSQL, pas un enum DB. La valeur `"partial"` est immédiatement utilisable. Les lignes existantes avec `"executed"` restent valides.

## Changements par fichier

### Backend

**`engine.py`** — `_execute_order_hook()` :

- Calcul explicite de `filled_amount` et `remaining_amount`
- Si `filled_amount >= requested * 0.995` → `execution_status = "executed"`
- Si `0 < filled_amount < requested * 0.995` → `execution_status = "partial"`
- Si `filled_amount == 0` → `execution_status = "failed"` avec `failure_reason = "zero_fill"`
- Champ `can_retry_remaining` ajouté dans `metadata_` (flag pour usage futur)
- Logique d'idempotence et de retry inchangée

**`metrics.py`** :

| Nouveau compteur | Description |
|-----------------|-------------|
| `orders_partial_remaining_volume` | Volume cumulé non exécuté sur les fills partiels |

Le compteur `orders_partial_fills` existant reste et est incrémenté quand `execution_status = "partial"`.

**`orders_router.py`** — `_order_to_response()` :

Nouveaux champs dans la réponse API :

| Champ | Type | Description |
|-------|------|-------------|
| `filled_amount` | `float?` | Montant effectivement exécuté |
| `remaining_amount` | `float?` | Montant restant non exécuté |
| `can_retry_remaining` | `bool` | Flag pour retry futur (toujours `false` pour executed, `true` pour partial) |

Aucun champ existant supprimé — rétrocompatibilité totale.

### Flutter

**`trigger_order.dart`** :

Nouveaux champs :
- `filledAmount` (`double?`)
- `remainingAmount` (`double?`)
- `canRetryRemaining` (`bool`)
- `isPartial` getter (`executionStatus == 'partial'`)

**`orders_list_screen.dart`** :

- Badge `"Partiel"` en orange pour `isPartial`
- Icône `pie_chart_rounded` en orange dans le trailing
- Subtitle format : `"Exécuté : X / Y EUR"` ou `"Exécuté : X / Y BTC"`
- Aucun changement pour les statuts `executed` et `failed` existants

## Metadata enrichie

### Ordre complet (`executed`)

```json
{
  "execution_price": 84250.5,
  "filled_amount": 100.0,
  "remaining_amount": 0.0,
  "partial_fill": false,
  "can_retry_remaining": false,
  "attempts": 1
}
```

### Ordre partiel (`partial`)

```json
{
  "execution_price": 84250.5,
  "filled_amount": 72.5,
  "remaining_amount": 27.5,
  "partial_fill": true,
  "can_retry_remaining": true,
  "attempts": 1
}
```

### Zero-fill (`failed`)

```json
{
  "failure_reason": "zero_fill",
  "filled_amount": 0,
  "remaining_amount": 100.0,
  "attempts": 2
}
```

## Compatibilité ascendante

- Les clients existants qui ne lisent pas `"partial"` le traiteront comme un statut inconnu (pas de crash, affichage neutre)
- Les lignes existantes en base avec `"executed"` restent valides et sont affichées normalement
- Les nouveaux champs API (`filled_amount`, `remaining_amount`, `can_retry_remaining`) sont nullable/optionnels — les clients anciens les ignorent
- Le flag `can_retry_remaining` est posé mais aucune logique de retry automatique n'est implémentée (hook futur)

## Hook futur : retry du remaining

Le champ `can_retry_remaining: true` permet une extension future où :
1. Un job background détecte les ordres avec `execution_status = "partial"` et `can_retry_remaining = true`
2. Il tente de réexécuter le `remaining_amount`
3. Si succès → `execution_status = "executed"`
4. Pas implémenté dans cette version, juste le flag préparatoire
