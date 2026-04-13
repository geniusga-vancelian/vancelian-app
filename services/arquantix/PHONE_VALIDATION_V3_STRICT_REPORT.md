# Phone validation V3 — strict fintech / compliance

## Executive Summary

La validation téléphone est désormais **MOBILE uniquement** en environnement **production-like** (`ENVIRONMENT` / `APP_ENV` ∈ `production`, `prod`, `live`). Le routage des politiques au submit utilise un **`policy_scope` explicite** (props composant, puis `field_definitions.policy_scope`, puis défauts documentés par `component_type`). Les réponses d’échec exposent un **`risk_signal`** et, en mode debug contrôlé, un objet **`debug`** avec les clés contractuelles `normalized`, `region`, `type`, `allowed`. Un **événement d’audit** `registration.phone.validated` enregistre chaque tentative (valeurs masquées).

## Mobile-Only Policy Decision

- **Accepté** : `phonenumbers.PhoneNumberType.MOBILE` uniquement en production-like.
- **Refusé** : `FIXED_LINE`, `FIXED_LINE_OR_MOBILE`, `VOIP`, `TOLL_FREE`, `PREMIUM_RATE`, `PAGER`, `UNKNOWN`, etc.
- **Dérogation QA** : hors production-like, si `PHONE_VALIDATION_DEBUG=true` **et** `PHONE_ALLOW_FIXED_LINE_OR_MOBILE=true`, `FIXED_LINE_OR_MOBILE` est également accepté (tests / banc d’essai uniquement — **jamais** lorsque `_is_production_like()` est vrai).

## Policy Scope Introduction

- **Valeurs** : `phone`, `residence`, `nationality`, `none`.
- **Résolution** (`policy_scope.resolve_policy_scope`) :
  1. `phone_input` → toujours `phone` (un `policy_scope` divergent dans les props est ignoré avec log warning).
  2. Sinon `props_json.policy_scope` si valide.
  3. Sinon `field_definition.policy_scope` (relation chargée au submit via `selectinload`).
  4. Sinon `country_picker` → défaut `residence` (les écrans **nationalité** doivent porter `policy_scope: nationality` dans les props ou en base).
  5. Sinon `none`.
- **Migration 103** : colonne `field_definitions.policy_scope` + backfill + `props_json.policy_scope` sur composants existants (téléphone, résidence, nationalité).

## Backend Validation Flow

1. Parse (`+` sans région ; national **uniquement** avec ISO2 sélectionné ou défaut jurisdiction mappable, sinon erreur de parse explicite).
2. `is_possible_number`
3. `is_valid_number`
4. Type strict SMS (MOBILE en prod)
5. Cohérence pays sélectionné (si fourni)
6. Allowlist téléphone juridiction (si activée)

`default_phone_region_iso2` ne retourne plus `FR` pour un code produit inconnu : **`None`** → pas de parsing national « silencieux » sans indicatif pays ou `+`.

## Flutter Simplification

- Saisie brute + pays : `onPhoneNationalChanged` remplit `{slug}` et `{slug}_raw`.
- `_onFieldChanged` duplique `{slug}_country_code` → `{slug}_country_iso2` pour alignement avec le contrat API.
- Aucune normalisation métier dans `AppPhoneInput` (déjà en place en V2).

## Error UX Improvements

- Messages backend / Flutter alignés :
  - `unsupported_phone_country` → *not supported for **your** jurisdiction*.
  - `phone_country_mismatch` → *does not match the selected country*.
- Modale DS : `headline` + `messageTitle` + `messageCaption` (hint API).

## Test Matrix

- **Backend** : FR/DE/ES/IT/AE mobiles E.164 OK ; fixe FR rejet ; US toll-free rejet ; national FR sans région → rejet ; national FR + `FR` OK ; Mexique `FIXED_LINE_OR_MOBILE` rejet en prod-like ; relax non-prod+debug+env ; mismatch pays ; `risk_signal` LOW / BLOCKED.
- **Juridiction** : composants de test avec `props_json.policy_scope` explicite.
- **Interaction SMS** : numéro national français avec `phone_number_raw` + `phone_number_country_code` / `_country_iso2`.

## Audit Logging

- Événement **`registration.phone.validated`** (`RegistrationEventType.PHONE_VALIDATED`) avec payload structuré : `raw_input` / `normalized` masqués (`mask_phone`), `region`, `type`, `type_label`, `jurisdiction`, `result` (`accepted` | `rejected`), `error_code`, `risk_signal`, `field_slug`.

## Risk Scoring Readiness

- Champ **`risk_signal`** sur `PhoneValidationResult` : `LOW`, `MEDIUM`, `HIGH`, `BLOCKED` (heuristique actuelle : succès EU/AE/low-risk regions → `LOW` ; allowlist téléphone refusée → `HIGH` ; échecs → `BLOCKED`). Non utilisé comme garde-fou produit pour l’instant.

## Remaining Gaps (should be NONE)

- **Aucun écart fonctionnel identifié** pour le périmètre V3 : exécuter `alembic upgrade head` jusqu’à **103** sur tous les environnements avant déploiement ORM.
- **Enrichissement runtime** des `country_picker` conserve un **pont legacy** : si `policy_scope` absent, `binding_slug == nationality` sélectionne encore la politique nationalité côté **enrichissement** uniquement (pas au submit).
