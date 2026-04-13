# Registration progress — durcissement multi-session

## Limite initiale

La **dernière** session seule déterminait `registration_completed`. Si une inscription avait été **terminée** puis une **nouvelle** session `in_progress` ouverte (re-parcours, test, nouveau flow), la progression pouvait « redescendre » alors que le métier considérait l’inscription déjà complétée une fois.

## Règle multi-session retenue

| Concept | Règle |
|--------|--------|
| **Snapshot runtime** | Toujours la session **la plus récente** (`order_by updated_at DESC`) — ce que l’utilisateur a à l’écran. |
| **`registration_completed` (bool)** | `True` si **au moins une** ligne `registration_sessions` pour la personne a `status = 'completed'`. |
| **Jalons registration (identity, terms, …)** | Comme avant pour l’union profil / étapes, mais le flag « tout complété » suit **`registration_completed`** au sens **historique** (any completed). |
| **Indicateur produit** | `session_snapshot.has_older_completed_session` : `True` quand il existe une session completed **et** que la session **la plus récente** n’est **pas** `completed` (nouvelle session en cours après une inscription déjà bouclée). |

## Hiérarchie exacte

1. **Lifecycle / KYC** : s’appuie sur `registration_completed` (any session completed).
2. **Macro** : inchangée dans l’ordre de priorité ; avec `registration_completed` restauré, `kyc_pending` redevient cohérent après re-parcours.
3. **`source_notes`** : inclut `any_reg_session_completed=…`, `has_older_completed_vs_latest_runtime=…`, et `sot=multi_session_completed_any_plus_latest_runtime_union_profile`.

## Impact `session_snapshot`

- Toujours la **dernière** session (statut, step, %).
- **`has_older_completed_session`** : aide support / admin à lire « inscription déjà terminée dans le passé + nouveau parcours ouvert ».

## Impact admin / Customer 360

- Les consommateurs JSON voient le nouveau champ sur le snapshot ; pas d’obligation de changer l’UI liste tant que les badges macro restent corrects.

## Exemples

- **Ancienne completed + nouvelle in_progress** : `registration_completed=true`, snapshot `in_progress`, `has_older_completed_session=true`.
- **Une seule session completed** : `has_older_completed_session=false`.

## Fichiers

- `api/services/customers_admin/registration_progress.py`, `schemas.py` (`RegistrationSessionSnapshot`)
- `api/tests/test_customers_admin_registration_progress.py` (`test_multi_session_old_completed_new_in_progress`)
