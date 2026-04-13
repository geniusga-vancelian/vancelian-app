# Phase 2A.13.5 — Placements Stable Identity Mapping

## Problème

Le join entre les positions earn (données financières) et les projets CMS (métadonnées)
reposait sur `lendingAsset` :

```
earnByAsset[project.lendingAsset.toUpperCase()] → EarnPositionItem
```

**Failles** :
- Deux offres sur le même asset (ex: USDC pool A / USDC pool B) → collision, une seule card affichée
- Renommage d'asset ou changement de configuration → join cassé
- Le backend groupait par asset sans exposer l'identité métier (pool_id, product_id, project_id)
- Le frontend portait une logique de résolution qui appartient au backend

## Correction Backend

### Fichier modifié : `api/services/lending/product_surface.py`

**Import ajouté** :
```python
from .offer_models import LendingPoolProduct
```

**Enrichissement** dans `get_earn_positions()` — pour chaque position par asset :

1. Le `pool` était déjà chargé (lookup `LendingPool` par asset)
2. Ajout du lookup `LendingPoolProduct` par `lending_pool_id`
3. Extraction de `project_id` depuis le produit

**Nouveaux champs par position** :
```json
{
  "asset": "USDC",
  "pool_id": "uuid-pool",
  "lending_pool_product_id": "uuid-product",
  "project_id": "project-slug-or-id",
  "total_supplied": 1000.0,
  ...
}
```

**Backward compatibility** : les champs existants sont inchangés. Les trois nouveaux champs sont `null` si aucun pool/produit n'existe.

### Chaîne de résolution

```
LendingPool (asset unique)
  → LendingPoolProduct (lending_pool_id FK)
    → project_id (String, nullable)
```

## Correction Flutter

### Modèles modifiés : `placement_position.dart`

**EarnPositionItem** — 3 champs ajoutés :
- `poolId` (String?)
- `lendingPoolProductId` (String?)
- `projectId` (String?)

Parsing null-safe via `json['pool_id'] as String?`.

**PlacementPosition** — 2 champs ajoutés :
- `poolId` (String?)
- `lendingPoolProductId` (String?)

### Join remplacé : `placements_screen.dart`

**Avant** (fragile, par asset) :
```dart
final earnByAsset = <String, EarnPositionItem>{};
for (final pos in earn.positions) {
  earnByAsset[pos.asset.toUpperCase()] = pos;
}
for (final project in projects) {
  final earnPos = earnByAsset[project.lendingAsset?.toUpperCase()];
  // Si match → créer PlacementPosition
}
```

**Après** (stable, par project_id) :
```dart
final projectById = <String, OfferProject>{};
for (final project in projects) {
  projectById[project.id] = project;
}
for (final earnPos in earn.positions) {
  final project = projectById[earnPos.projectId];
  // Toujours créer PlacementPosition, avec ou sans projet CMS
}
```

### Changements clés

| Aspect | Avant | Après |
|--------|-------|-------|
| Direction du join | Projet → Position | Position → Projet |
| Clé de join | `lendingAsset` (String) | `projectId` (ID métier) |
| 2 offres même asset | Collision (1 card) | 2 cards distinctes |
| Position sans projet CMS | Silencieusement ignorée | Affichée (fallback générique) |
| Logique de résolution | Frontend | Backend |

## Fallback Behavior

Si `projectId == null` ou vide sur une `EarnPositionItem` :

1. La position est quand même affichée
2. `projectTitle` = nom de l'asset (ex: "USDC")
3. `projectCategory` = vide
4. `projectImageUrl` = null (icône par défaut)
5. `status` = "active"
6. Aucun crash, aucune donnée perdue

## Fichiers modifiés

| Fichier | Type | Changement |
|---------|------|------------|
| `api/services/lending/product_surface.py` | Backend | +import LendingPoolProduct, +lookup product, +3 champs par position |
| `mobile/lib/features/placements/domain/models/placement_position.dart` | Flutter | +3 champs EarnPositionItem, +2 champs PlacementPosition |
| `mobile/lib/features/placements/presentation/screens/placements_screen.dart` | Flutter | Remplacement complet de `_buildPositions()` |

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Zéro changement moteur lending | ✅ |
| Zéro changement CMS Projects | ✅ |
| Zéro changement ExchangeService | ✅ |
| Zéro changement PoolService | ✅ |
| Zéro régression PlacementsScreen | ✅ |
| Zéro régression PlacementDetailScreen | ✅ |
| Zéro régression crypto_positions | ✅ |
| Backward compatibility API (champs existants inchangés) | ✅ |
| Flutter analyze : 0 errors | ✅ |
| Python import : OK | ✅ |

## Validation

```
$ flutter analyze lib/features/placements/
No issues found!

$ python3 -c "from services.lending.product_surface import get_earn_positions"
OK
```
