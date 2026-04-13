# Registration progress — modèle canonique (Customer 360)

## Executive summary

La progression client est désormais calculée **uniquement côté backend** dans `compute_canonical_registration_progress`, avec trois blocs :

1. **Foundation** — juridiction, mobile collecté, OTP SMS vérifié (`two_factor_challenges`), passcode serveur si présent dans `profile_json.security`, session d’inscription initialisée.
2. **Registration** — drapeaux alignés sur les étapes du flow EU v2 (`identity` … `terms`), dérivés du **profil collecté** et/ou des **états de session** (`registration_session_steps`), avec complétion globale si `registration_sessions.status = completed`.
3. **Lifecycle** — `person.kyc_status`, lien `pe_clients`, statut actif.

Un **stade macro** unique (`RegistrationMacroStage`) est choisi par priorité déterministe ; un **legacy_stage** (`RegistrationProgressStage`) est conservé pour comparaisons. Le **ratio** combine 20 % fondation + 50 % registration + 30 % lifecycle (voir ci-dessous).

## Modèle canonique retenu

| Champ | Rôle |
|--------|------|
| `stage` | `RegistrationMacroStage` (valeur API : string) |
| `label` | Libellé FR lisible support |
| `completion_ratio` | Float 0–1 |
| `completed_steps` / `missing_steps` | Clés préfixées `foundation:`, `registration:`, `lifecycle:` |
| `foundation` | `FoundationState` |
| `registration` | `RegistrationStateFlags` |
| `lifecycle` | `LifecycleState` |
| `session_snapshot` | `RegistrationSessionSnapshot` (dernière session) |
| `legacy_stage` | Ancien regroupement |

## Source of truth

| Signal | Source |
|--------|--------|
| Juridiction | `persons.jurisdiction` |
| Mobile collecté | `profile_json.collected.*` (slugs téléphone habituels) |
| Mobile vérifié (OTP) | `two_factor_challenges` : `channel` SMS + `status = verified` |
| Passcode | `profile_json.security.passcode_set` / `passcode_enabled` si présents ; sinon `null` (souvent **local device** uniquement — non inféré) |
| Session | Dernière `registration_sessions` par `updated_at` ; `flow_version`, `current_step_id` / `current_screen_id` résolus via ORM |
| Champs registration | `get_person_collected_value` + statuts d’étapes session (`completed` / `skipped`) |
| KYC | `persons.kyc_status` |
| PE / actif | `pe_clients` lié à `person_id`, `status` |

**Dérivé** : `macro_stage`, `completion_ratio`, listes completed/missing, flags booléens registration.

## Règles de calcul — stade macro (ordre)

1. `active_client` — `pe_clients.status == active`
2. `pe_client_linked` — ligne `pe_clients` présente
3. `kyc_completed` — `kyc_status` ∈ {`approved`, `verified`}
4. `registration_completed` — session `status == completed`
5. `registration_in_progress` — session existe et non complétée
6. `kyc_pending` — KYC ni terminé ni vide/rejeté (heuristique)
7. `account_secured` — mobile vérifié + passcode non « faux » côté profil
8. `phone_started` — mobile collecté

## completion_ratio

- **Fondation** : moyenne de 4 booléens (juridiction, mobile, OTP vérifié, session) ; +0,05 si `passcode_created is True` (plafonné à 1).
- **Registration** : nombre d’étapes canoniques complétées / 7.
- **Lifecycle** : 0 / 0,25 / 0,55 / 0,75 / 1,0 selon absence → pending KYC → KYC complété → PE lié → actif.

Formule : `0,2 × fondation + 0,5 × registration + 0,3 × lifecycle` (arrondi 3 décimales).

Philosophie : pondération explicite, pas de double comptage des mêmes faits dans deux bandes ; la part « lifecycle » reste modérée tant que le parcours métier n’est pas finalisé.

## Endpoints / services impactés

- `services/customers_admin/registration_progress.py` — logique centrale.
- `services/customers_admin/schemas.py` — schémas étendus.
- `services/customers_admin/service.py` — `get_customer_detail` utilise un seul appel canonique + résumé session enrichi.
- `tests/test_customers_admin_registration_progress.py` — couverture scénarios clés.

## Impacts admin (web)

- Liste : badges de couleur étendus aux nouveaux `stage` (`registration_*`, `account_secured`, `kyc_completed`).
- Fiche : affichage `legacy_stage`, champs session (`flow_version`, `current_step_key`, `current_screen_key`), blocs JSON **Fondation / Registration / Lifecycle** (lisibles support).

## Compatibilité & extensions

- Nouvelles étapes registration : ajouter la clé dans `reg_keys` et dans `_pick` / profils.
- Passcode serveur : dès qu’une clé standard est écrite dans `profile_json.security`, le booléen se remplit sans changer le contrat API.
- i18n des libellés admin : aujourd’hui libellés FR en dur dans `_MACRO_LABELS_FR` — possible de les externaliser.

## Fichiers

- `api/services/customers_admin/registration_progress.py`
- `api/services/customers_admin/schemas.py`
- `api/services/customers_admin/service.py`
- `api/tests/test_customers_admin_registration_progress.py`
- `api/alembic/versions/122_eu_registration_flow_v2_i18n_polish.py` (prompt 1)
- `web/src/app/admin/customers/page.tsx`, `[personId]/page.tsx`
