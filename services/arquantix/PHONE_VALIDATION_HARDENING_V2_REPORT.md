# Phone validation hardening V2 — Registration Engine

## Executive Summary

La validation téléphone du moteur d’inscription est recentrée sur le **backend** (libphonenumber), avec un **payload structuré** côté Flutter (`{slug}` + `{slug}_raw` + `{slug}_country_code`), des **codes d’erreur séparés** (parse / type / politique / mismatch), une politique **MOBILE vs FIXED_LINE_OR_MOBILE** pilotée par variable d’environnement, un **hint** optionnel pour le cas FR `+330…`, et un mode **debug QA** (`PHONE_VALIDATION_DEBUG`). Les flows existants restent compatibles : les clients qui n’envoient que `{slug}` (souvent E.164) continuent de fonctionner.

## Root Causes Found

1. **E.164 « maison » côté Flutter** : `normalizePhoneFieldToE164` concaténait indicatif + national et supprimait un seul `0`, créant des divergences avec la vérité métier et des faux positifs/négatifs sur certains formats EU.
2. **Décision de validité partagée** : le client pouvait faire croire à un numéro « correct » alors que le type (fixe, VOIP, etc.) ou la politique juridictionnelle devait trancher.
3. **Messages et politiques mélangés** : risque de message « pays non autorisé » alors que le problème était un parse invalide — corrigé en enchaînant toujours parse → validité lib → type SMS → allowlist juridiction.
4. **Titres / copy modale** : titres génériques et formulations « allowed » au lieu de « supported » pour la juridiction.

## Flutter Input Audit

- **`AppPhoneInput`** : ne appelle plus `normalizePhoneFieldToE164` ; `onPhoneChanged` transmet la **saisie telle quelle** (espaces conservés ; le backend compacte).
- **`RegistrationFlowRenderer`** : callback optionnel `onPhoneNationalChanged` pour mettre à jour **`slug` et `{slug}_raw`** en un seul `setState` (écran d’inscription).
- **`RegistrationFlowScreen`** : `_onPhoneNationalChanged` remplit les deux clés ; modale de confirmation utilise **`_formatConfirmPhonePreview`** (affichage seulement, pas de règle métier) ; rechargement session : si seul `slug` est présent dans les données collectées, **`{slug}_raw`** est aligné pour le submit.
- **`normalizePhoneFieldToE164`** : **conservé** dans `core/phone_e164.dart` avec documentation « legacy / tests », **hors** chemin submit registration.

## Backend Validation Audit

- **`validators.py`** : pas de regex téléphone métier (inchangé dans cette phase).
- **`jurisdiction_policy_submit.py`** : au submit, lecture prioritaire de **`{slug}_raw`**, sinon **`{slug}`** (legacy) ; normalisation E.164 écrite dans **`answers[slug]`** après succès.
- **`service.submit_screen`** : champs obligatoires — pour `phone_input`, présence satisfaite si **`slug` ou `{slug}_raw`** est non vide.
- **`ValidationError`** : champs optionnels **`message_hint`**, **`debug_extra`** ; **`runtime_router` submit** les expose en JSON (`message_hint`, `debug`).

## Central Phone Validation Layer

Fichier : `api/services/registration/phone_validation.py`.

API publique (documentée dans le module) :

- `parse_phone_input(raw_value, selected_country_iso2, *, jurisdiction_default_region=...)`
- `normalize_phone_to_e164(...)` / alias historique `normalize_to_e164`
- `classify_phone_number(...)` — métriques lib (possible / valid / type / SMS-compatible), **sans** allowlist juridiction (`is_policy_allowed` reste `False` dans ce chemin).
- `validate_mobile_phone_for_jurisdiction(...)` — mobile + cohérence pays sélectionné + allowlist téléphone si activée.

Résultat : **`PhoneValidationResult`** avec `raw_input`, `selected_country_iso2`, `normalized_e164`, `region_code`, `country_calling_code`, `number_type`, `is_possible`, `is_valid`, `is_mobile_compatible`, `is_policy_allowed`, `error_code`, `user_message`, `message_hint`, `debug`.

## Mobile Type Policy

- **Toujours accepté** : `MOBILE`.
- **`FIXED_LINE_OR_MOBILE`** : accepté **uniquement** si `PHONE_ALLOW_FIXED_LINE_OR_MOBILE` vaut une vérité (`true` / `1` / `yes` / `on`). **Défaut : `true`** (compatibilité avec les plans de numérotation ambigus). Pour un posture fintech stricte, fixer à `false` en déploiement.
- **Refus explicite** : `FIXED_LINE` pur, `VOIP`, `PREMIUM`, `TOLL_FREE`, `PAGER`, `UNKNOWN`, etc.

## Jurisdiction Policy Integration

1. Parse avec `+` → `parse(..., None)` ; sinon national → `parse(..., region)` où region = **ISO2 sélectionné** si valide, sinon **`default_phone_region_iso2(jurisdiction)`** (EU→FR, UAE→AE, code ISO2 2 lettres sinon FR).
2. Après numéro **possible + valide** et **type SMS OK** : contrôle **pays réel** (`region_code_for_number`) vs **pays sélectionné** si fourni → `phone_country_mismatch`.
3. Si allowlist téléphone active pour la juridiction → `is_phone_country_allowed` → `unsupported_phone_country` (message : *not supported for the selected jurisdiction*).
4. Les erreurs de parse / validité lib restent **`invalid_phone_number`** (pas confondues avec la politique pays).

## Error Modal UX

- Mapping Flutter dans `registration_phone_user_errors.dart` : titres et messages alignés sur la spec (Invalid phone number, Unsupported number, Unsupported phone number, Country code mismatch).
- **`message_hint`** du backend affiché en **`messageCaption`** du `DsValidationResultBody` (DS officiel).
- Pas d’erreur inline technique sous le champ téléphone : `showInlineError: false` conservé sur `AppPhoneInput` dans le renderer.

## Test Matrix (EU + UAE)

| Cas | Attendu |
|-----|---------|
| E.164 mobiles FR, DE, ES, IT, BE, NL, PT, IE, AE | Accepté (normalisé identique si déjà E.164) |
| National + espaces + ISO2 sélectionné (échantillons par pays) | Accepté → E.164 attendu |
| FR fixe `+33123456789` | `phone_number_not_mobile` |
| MX `+525512345678` (FIXED_LINE_OR_MOBILE) + `PHONE_ALLOW_FIXED_LINE_OR_MOBILE=false` | `phone_number_not_mobile` |
| Même MX + allow FL_OR_MOBILE=true | Accepté |
| `+336…` saisi, pays picker `DE` | `phone_country_mismatch` |
| Saisie invalide / `+330…` aberrant | `invalid_phone_number` ; hint FR si motif `+330\d` |
| Legacy : uniquement `phone_number` (E.164) sans `_raw` | Toujours traité |

## Tests Added

- **Backend** : `api/tests/test_registration_phone_validation.py` — matrice E.164 EU+AE, nationaux formatés, hint FR, politique FL_OR_MOBILE, mismatch pays, régressions existantes.
- **Flutter** : `registration_renderer_test` (AppPhoneInput, `onPhoneNationalChanged`), `registration_phone_user_errors_test` (titres / messages), `phone_e164_test` (legacy helper inchangé).

## Remaining Gaps / Next Steps

1. **`policy_scope`** sur les définitions de champs (ex. `phone`, `residence`, `nationality`) : **non migré en base** dans cette phase ; stratégie : ajouter une colonne / clé JSON sur les composants ou `field_definitions`, router les validateurs par scope, déprécier l’inférence par slug seul. TODO tracé en en-tête de `phone_validation.py` et dans ce rapport.
2. **Persistance `{slug}_raw`** : le submit enregistre toutes les clés présentes dans `answers` ; `phone_number_raw` peut être stocké en session pour audit — à documenter côté conformité / rétention.
3. **Modale** : pas de test E2E widget sur `RegistrationFlowScreen` + Modale (lourd) ; couverture via mapping + API 422 structurée.
4. **Debug** : `debug` dans le JSON 422 ne doit être activé qu’en QA ; vérifier qu’aucun client prod ne dépend de ce champ.

## Risques résiduels

- **Plans de numérotation** : évolution des métadonnées libphonenumber / pays ; tests à maintenir.
- **`PHONE_ALLOW_FIXED_LINE_OR_MOBILE=false`** : peut rejeter des numéros réellement mobiles mais classés `FIXED_LINE_OR_MOBILE` dans certaines régions — choix produit à monitorer.
- **Reprise de session** : si l’utilisateur a un E.164 stocké, l’UI affiche la valeur brute collectée ; pas de re-split national côté client (évité volontairement pour ne pas réintroduire de logique maison).
