# Phase 4C.6 — Score de confiance (shutdown legacy persons)

## Objectif

Enrichir la sortie Phase 4C.4 avec un **`confidence_score`** (0.0–1.0) et une **`confidence_band`** lisibles par produit / ops, **sans** modifier la logique **`ready`** ni les **`recommendation`** existantes.

## Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `api/services/persons/legacy_persons_shutdown_readiness.py` | Calcul déterministe du score, bande d’interprétation, champs ajoutés au résultat et au JSON. |
| `api/tests/test_legacy_persons_shutdown_readiness.py` | Tests score, pénalités combinées, clamp, stabilité des clés JSON. |

## Formule de score (déterministe)

Point de départ : **1.0**. Soustractions (indépendantes de `ready`) :

| Condition | Pénalité |
|-----------|----------|
| `unauthenticated_hits > 0` | **−0.5** |
| `max_total_hits > 0` et `total_hits > max_total_hits` | **−0.2** |
| `max_admin_hits >= 0` et `admin_hits > max_admin_hits` | **−0.2** |
| `max_owner_hits >= 0` et `owner_hits > max_owner_hits` | **−0.1** |
| Preuve successeur requise et `successor_identity_hits < min_successor_identity_hits` | **−0.2** |

Puis **clamp** dans **[0.0, 1.0]**. Affichage JSON : `confidence_score` arrondi à **4** décimales.

### Cas particuliers (hors formule traffic)

| Situation | `confidence_score` | `confidence_band` |
|-----------|-------------------|-------------------|
| Flag legacy déjà désactivé (`already_disabled`) | 1.0 | `very_safe` |
| `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_BLOCK` | 0.0 | `not_safe` |
| `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_READY` | 1.0 | `very_safe` |

## `confidence_band` (compact)

| Valeur | Plage de score |
|--------|----------------|
| `very_safe` | ≥ 0.9 |
| `mostly_safe` | ≥ 0.7 et < 0.9 |
| `caution` | ≥ 0.4 et < 0.7 |
| `not_safe` | < 0.4 |

## Exemples de JSON

### Trafic nul, critères OK

```json
{
  "ready": true,
  "confidence_score": 1.0,
  "confidence_band": "very_safe",
  "blocking_reasons": [],
  "recommendation": "disable_in_staging_first",
  "traffic_summary": { "total_hits": 0, "unauthenticated_hits": 0, "admin_hits": 0, "owner_hits": 0 }
}
```

### Trafic non authentifié (pénalité −0.5)

```json
{
  "ready": false,
  "confidence_score": 0.5,
  "confidence_band": "caution",
  "blocking_reasons": ["unauthenticated_traffic_above_threshold"],
  "recommendation": "keep_enabled"
}
```

### Toutes les pénalités applicables (clamp à 0.0)

Somme des pénalités > 1.0 → `confidence_score` = **0.0**, `confidence_band` = **not_safe**.

## Interprétation pour les parties prenantes

- **`ready`** reste la **décision binaire** (go/no-go selon seuils configurés).
- **`confidence_score`** résume **à quel point** le contexte observé est « sain » pour une désactivation, même lorsque des signaux se cumulent (ex. trafic non auth + volume élevé).
- Un **`ready=true`** avec un score modéré peut arriver si la configuration est tolérante alors que le score reflète encore du risque résiduel — d’où l’intérêt des deux champs.

**Confirmation** : aucune politique d’enforcement n’est changée ; pas d’aléa ; le booléen **`ready`** reste **autoritaire** pour l’automatisation ou les runbooks qui ne consomment qu’un seul champ.

## Références

- Phase 4C.4 : `PHASE_4C4_LEGACY_PERSONS_SHUTDOWN_READINESS.md`
- Métriques : `PHASE_4C3_LEGACY_PERSONS_AGGREGATED_METRICS.md`, `PHASE_4C5_ROLLING_WINDOW_METRICS.md`
