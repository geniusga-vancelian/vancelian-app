# Registration progress — priorité session vs `profile_json`

## Conflit initial

Le même calcul mélangeait données **runtime** (`registration_sessions`) et **persistées** (`profile_json.collected`) sans règle explicite, ce qui pouvait produire des incohérences customer 360 / dashboard.

## Règle canonique retenue

Implémentée dans `_registration_flags_with_source_priority` :

1. **Session la plus récente** : `_latest_registration_session` (tri `updated_at` / création).
2. **Si `session.status == "completed"`** : tous les jalons registration considérés **complétés** (vérité lifecycle « inscription terminée » + projection profil attendue).
3. **Sinon** : pour chaque étape (`identity`, `date_of_birth`, …) — **complété** si :
   - l’étape est marquée faite / skippée dans la session courante, **ou**
   - le profil contient déjà les données requises (union ordonnée).

`source_notes` inclut `sot=session_latest_or_profile_union`.

## Hiérarchie source of truth

| Couche | Rôle |
|--------|------|
| **Session (dernière)** | Runtime : `status`, `current_step`, `progress_percent`, étapes `RegistrationSessionStep` |
| **profile_json.collected** | Persistance durable ; comble les trous si la session n’a pas encore marqué l’étape |
| **Session `completed`** | Bascule forte : tous les flags registration à vrai |

## `session_snapshot`

Reflet de la **dernière** session : `session_id`, `status`, `flow_id`, `flow_version`, `current_step_key`, `current_screen_key`, `progress_percent`, `updated_at`. Il ne remplace pas les flags registration dérivés (qui utilisent la règle d’union ci-dessus).

## Flags `registration.*` (identity, dob, …)

- Dérivés de la **fonction `pick`** : étape session **ou** profil, avec override **tout vrai** si session **completed** (et email verification optionnel forcé à vrai dans ce cas).

## Exemples

- **Profil riche, session incomplète** : les jalons passent à vrai dès que les données sont en profil (ex. test `test_profile_fills_step_when_session_not_marked`).
- **Ancienne session complétée + nouvelle session** : seule la **dernière** session compte pour `reg_completed` et le snapshot ; si la dernière n’est pas `completed`, `registration_completed` reste faux même si une ancienne l’était (comportement à surveiller côté produit si re-inscription).

## Impact admin / customer 360

- Un seul endroit backend calcule la progression ; les listes `completed_steps` / `missing_steps` restent alignées sur la même règle.

## Limites restantes

- Multi-session « historique » : pas de fusion cross-sessions au-delà de la **latest** ; documenté pour éviter les surprises si le métier autorise plusieurs sessions actives.
