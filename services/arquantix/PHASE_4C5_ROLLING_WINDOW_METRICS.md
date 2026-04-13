# Phase 4C.5 — Métriques à fenêtre glissante (legacy persons)

## Objectif

Compléter les compteurs Phase 4C.3 (cumul process-lifetime + séries labellisées) avec des **totaux récents** exploitables pour les décisions de shutdown : **24 heures** et **7 jours**, sans stockage externe ni nouvelle dépendance.

## Fichiers modifiés / ajoutés

| Fichier | Modification |
|---------|--------------|
| `api/services/persons/legacy_persons_metrics.py` | `deque` d’horodatages UTC (float, secondes) par hit ; élagage ; plafond mémoire ; champs ajoutés dans `snapshot()`. |
| `api/tests/test_legacy_persons_rolling_metrics.py` | **Nouveau** — couverture 24h / 7j, cumul inchangé, borne mémoire, absence d’UUID dans le snapshot. |

## Format `snapshot()` (extension rétrocompatible)

Les clés existantes (`metric`, `legacy_persons_endpoint_hit_total`, `series`) sont **inchangées**. Deux clés sont **ajoutées** :

```json
{
  "metric": "legacy_persons_endpoint_hit_total",
  "legacy_persons_endpoint_hit_total": 12345,
  "last_24h_hits": 12,
  "last_7d_hits": 89,
  "series": [ ... ]
}
```

Constantes exportées côté module : `LAST_24H_HITS` (`"last_24h_hits"`), `LAST_7D_HITS` (`"last_7d_hits"`).

## Stratégie d’élagage (pruning)

1. **À chaque `record_hit`** et **à chaque `snapshot()`** : suppression des horodatages **strictement plus anciens que maintenant − 7 jours** (UTC), en retirant par la gauche du `deque` (FIFO).
2. **Plafond dur** `_MAX_ROLLING_TIMESTAMPS` (**100 000**) : après l’élagage 7 jours, tant que la taille dépasse ce plafond, on retire les plus anciens. Cas limite : charge extrême sur une fenêtre courte ; les totaux glissants peuvent alors **sous-estimer** le trafic réel, mais la mémoire reste bornée.

Aucun identifiant personne ni PII : un enregistrement = **un seul float** (timestamp UTC).

## Mémoire et sûreté

- **Borne supérieure** : au plus **100 000** floats (~800 Ko) pour la file d’horodatages, en plus des compteurs cumulatifs et des séries à faible cardinalité existants.
- **Thread-safety** : tout passe par le verrou existant (`RLock` équivalent via `threading.Lock`).
- Le total **`legacy_persons_endpoint_hit_total`** reste le **cumul depuis le démarrage du process** ; il n’est **pas** réduit par l’élagage.

## Intérêt pour les décisions de shutdown (vs cumul seul)

| Indicateur | Usage |
|------------|--------|
| `last_24h_hits` | Détecter un **pic récent** ou confirmer **quasi-zéro** sur la dernière journée avant de couper `ALLOW_LEGACY_UNAUTHENTICATED_KYC`. |
| `last_7d_hits` | Vue **hebdo** pour distinguer traîne legacy résiduelle d’un **historique** élevé accumulé depuis des mois (cumul process). |
| Cumul `legacy_persons_endpoint_hit_total` | Contexte « depuis déploiement » ; croiser avec redémarrages / réinitialisations. |

En complément : Phase 4C.4 (readiness) peut évoluer pour exploiter `last_24h_hits` / `last_7d_hits` dans un second temps (hors périmètre minimal de ce ticket).

## Références

- Phase 4C.3 : `PHASE_4C3_LEGACY_PERSONS_AGGREGATED_METRICS.md`
- Phase 4C.4 : `PHASE_4C4_LEGACY_PERSONS_SHUTDOWN_READINESS.md`
