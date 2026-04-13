# Phase 4C.7 — Intégration des fenêtres glissantes dans le readiness shutdown

## Objectif

Enrichir l’évaluation Phase 4C.4 / 4C.6 avec les compteurs **récent** `last_24h_hits` et `last_7d_hits` (Phase 4C.5) pour que le **go/no-go** reflète l’usage **actuel**, et pas seulement le cumul process-lifetime.

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `api/services/persons/legacy_persons_shutdown_readiness.py` | `summarize_traffic_from_metrics_snapshot` inclut `last_24h_hits` / `last_7d_hits` ; nouveaux seuils config + env ; nouvelles raisons de blocage ; pénalités optionnelles de `confidence_score` alignées sur les seuils récents. |
| `api/tests/test_legacy_persons_shutdown_readiness.py` | Tests cumul élevé / fenêtres nulles, dépassements 24h / 7j, rétrocompatibilité sans clés snapshot. |

`api/services/persons/legacy_persons_metrics.py` : **aucun changement** (les clés existent déjà).

## Nouvelles variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `LEGACY_SHUTDOWN_MAX_LAST_24H_HITS` | `0` | `0` = **désactivé** ; sinon `ready=false` si `last_24h_hits` **>** cette valeur. |
| `LEGACY_SHUTDOWN_MAX_LAST_7D_HITS` | `0` | Idem pour `last_7d_hits`. |

Champs correspondants dans `LegacyPersonsShutdownReadinessConfig` et dans `config_effective` du JSON : `max_last_24h_hits`, `max_last_7d_hits`.

## Logique de readiness (extension)

Les critères **cumulatifs** (non auth, total, admin, owner, preuve successeur) sont **inchangés**.

En **complément**, si le seuil est **> 0** :

- `last_24h_hits > max_last_24h_hits` → `blocking_reasons` contient **`recent_24h_traffic_above_threshold`**
- `last_7d_hits > max_last_7d_hits` → **`recent_7d_traffic_above_threshold`**

`ready` est **false** si une raison de blocage est présente (comme avant). **`recommendation`** suit toujours la même table (ex. `keep_enabled` si `not ready`).

**Rétrocompatibilité** : snapshot **sans** les clés Phase 4C.5 → `last_24h_hits` / `last_7d_hits` traités comme **0**. Avec seuils à **0**, aucun blocage nouveau (comportement identique à l’avant).

## `confidence_score` (Phase 4C.6)

Pénalités **informationnelles** supplémentaires lorsque les seuils récents sont dépassés (mêmes conditions que le blocage) : **−0.1** chacune. `ready` reste la **décision autoritaire**.

## Exemples de `traffic_summary`

```json
{
  "total_hits": 500,
  "unauthenticated_hits": 0,
  "admin_hits": 500,
  "owner_hits": 0,
  "last_24h_hits": 0,
  "last_7d_hits": 0
}
```

Cas typique : fort **historique** cumulé (ex. avant migration), mais **aucun** hit dans les 24h / 7j → peut être **ready** pour les fenêtres si les plafonds récents sont respectés, alors qu’un cumul seul aurait pu masquer un calme récent.

Exemple blocage 24h :

```json
{
  "blocking_reasons": ["recent_24h_traffic_above_threshold"],
  "traffic_summary": {
    "total_hits": 0,
    "unauthenticated_hits": 0,
    "admin_hits": 0,
    "owner_hits": 0,
    "last_24h_hits": 12,
    "last_7d_hits": 12
  },
  "config_effective": {
    "max_last_24h_hits": 10,
    "max_last_7d_hits": 0
  }
}
```

## Pourquoi c’est plus sûr pour le shutdown

- Le **cumul process** mélange l’historique lointain et l’activité récente ; après redémarrage il **retombe à zéro**, ce qui peut donner un faux sentiment de calme.
- Les fenêtres **24h / 7j** (Phase 4C.5) reflètent l’usage **récent** dans le même processus, mieux aligné avec « personne n’appelle plus le legacy **maintenant** » avant de couper `ALLOW_LEGACY_UNAUTHENTICATED_KYC`.

## Références

- Fenêtres : `PHASE_4C5_ROLLING_WINDOW_METRICS.md`
- Readiness / confiance : `PHASE_4C4_LEGACY_PERSONS_SHUTDOWN_READINESS.md`, `PHASE_4C6_SHUTDOWN_CONFIDENCE_SCORE.md`
