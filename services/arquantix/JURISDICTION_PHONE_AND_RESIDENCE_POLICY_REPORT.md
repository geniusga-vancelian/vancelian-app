# Jurisdiction phone & residence policy

## Executive Summary

Le produit impose des **listes autorisées par juridiction** pour le **pays d’indicatif téléphonique** (`phone_input` / `phone_number`) et le **pays de résidence** (`country_picker` / `country_of_residence`). La **source de vérité est la base PostgreSQL** (`country_directory`, `jurisdiction_country_policies`). Le **runtime d’inscription** enrichit les `props` des composants renvoyés à Flutter ; le **submit** est **revalidé côté API** avec des messages préfixés (`[PHONE_COUNTRY_NOT_ALLOWED]`, `[PHONE_COUNTRY_MISMATCH]`, `[RESIDENCE_COUNTRY_NOT_ALLOWED]`). Flutter **filtre l’UI** à partir des listes reçues, **sans règle métier codée en dur** sur les juridictions.

## Data Model

- **`public.country_directory`** : référentiel pays (`iso2`, `iso3`, noms EN/FR, `phone_country_code`, `is_active`, `created_at`).
- **`public.jurisdiction_country_policies`** : une ligne par couple `(jurisdiction_code, country_iso2)` avec `allow_residence`, `allow_phone_country_code`, `is_default`, `position`, `created_at`. Contrainte d’unicité sur `(jurisdiction_code, country_iso2)`. FK `country_iso2` → `country_directory.iso2`.

Migration Alembic : `api/alembic/versions/099_country_directory_jurisdiction_policies.py`.

## Seed Data

Seed **explicite** (pas d’inférence « toute l’Europe ») pour les juridictions métier (**EU**, **EU_VS**, **UAE**) + référentiel pays nécessaire. **UAE** : **AE** seulement pour téléphone et résidence. **EU / EU_VS** : liste européenne/EEA alignée produit. Téléphone par défaut seedé : **FR** (EU), **AE** (UAE).

## Runtime Enrichment

Fichier : `api/services/registration/jurisdiction_policies.py` — `enrich_registration_component_props(db, jurisdiction_code, component_type, props, ...)`.

- **`phone_input`** : ajout de `allowed_phone_countries` (et `default_phone_country` si une ligne `is_default` existe).
- **`country_picker`** : ajout de `allowed_countries` (même forme d’objets : `iso2`, `dial_code`, `label_en`, `label_fr`, `is_default`).

Appel depuis `RegistrationFlowService._build_screen_response` après sérialisation de chaque composant visible (`api/services/registration/service.py`).

## Backend Validation

Fichier : `api/services/registration/jurisdiction_policy_submit.py` — `validate_jurisdiction_policies_on_submit`.

- Si **aucune policy téléphone** (resp. résidence) pour la juridiction, la partie correspondante est **ignorée** (rétrocompatibilité).
- **`phone_number`** : parsing E.164 via `phonenumbers`, contrôle du pays dérivé, optionnellement cohérence avec `{slug}_country_code`.
- **`country_of_residence`** (tout `country_picker` lié) : ISO2 autorisé pour la juridiction.

Branchement : `submit_screen` après validation des champs requis (`service.py`).

## Flutter Consumption

- **`AppPhoneInput`** (`mobile/lib/design_system/components/app_phone_input.dart`) : paramètres optionnels `allowedPhoneCountries` et `defaultPhoneCountryIso2` ; le sheet d’indicatifs utilise **uniquement** la liste fournie lorsqu’elle est non vide.
- **`AppCountryPicker`** : paramètre optionnel `allowedCountries` (`value` / `label` déjà localisés côté renderer).
- **`RegistrationFlowRenderer`** : lit `allowed_phone_countries`, `default_phone_country`, `allowed_countries` depuis `comp.props` et les transmet aux widgets.

## Tests Added

Fichier : `api/tests/test_registration_jurisdiction_country_policies.py`.

- Service : juridiction de test **JTEST_EU** (FR+DE) vs **JTEST_UAE** (AE seul).
- Enrichissement : `phone_input` et `country_picker`.
- Submit : scénarios FR accepté EU, AE refusé EU, +971 UAE, résidence FR refusée UAE, AE acceptée UAE.
- HTTP : `GET /api/admin/jurisdictions/{code}/country-policies`.

**Prérequis** : tables créées par migration (**099**). Si `public.country_directory` est absent, les tests sont **skipped** avec un message invitant à lancer `alembic upgrade head`.

## Remaining Gaps / Next Steps

- **Édition admin** : seul le **GET** est livré (`jurisdiction_country_admin_router.py`). POST/PATCH et garde d’auth alignée sur le reste de l’admin peuvent suivre.
- **Nationalité vs résidence** : aujourd’hui tout `country_picker` reçoit la même liste « résidence » et la validation submit suit les policies résidence pour chaque picker ; si la nationalité doit diverger, prévoir un second axe en base (ex. `allow_nationality` ou ciblage par `binding_slug`).
- **CI** : garantir `alembic upgrade head` (ou image DB à jour) pour que les tests ne restent pas en skip.
- **Serializeur admin / preview flow** : l’enrichissement policy est sur le **runtime session** ; un aperçu builder sans session peut ne pas montrer les listes tant qu’on ne duplique pas l’enrichissement sur ce chemin.
