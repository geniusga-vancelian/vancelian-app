# Jurisdiction policy admin — long-term design

## Executive Summary

Les **policies pays / téléphone par juridiction** sont désormais **administrables** hors du flow editor : modèle SQL durci (`is_default_residence` / `is_default_phone`, table `jurisdiction_policy_settings`), **API admin** transactionnelle (liste, détail, PATCH settings / countries, presets explicites), **UI Next.js** (`/admin/jurisdiction-policies`, `/admin/country-directory`) et **résumés** sur la liste registration + l’éditeur de flow. Le **runtime** (`jurisdiction_policies.py`) applique l’**héritage téléphone ← résidence** quand le flag global est actif. **Flutter** consomme toujours les listes et defaults **depuis l’API**, sans règles métier codées en dur.

## Why Policy Was Moved Out of Flow Editor

Un flow décrit des **écrans et composants** ; la **liste de pays autorisés** est une **contrainte réglementaire / produit** par juridiction, partagée entre flows et réutilisable. La mélanger au builder créait une source de vérité implicite et difficile à auditer. Désormais le flow **référence** une `RegistrationJurisdiction` ; la policy est **centralisée** et visible sur des pages dédiées.

## Data Model Hardening

- **`jurisdiction_country_policies`** : colonnes `is_default_residence` et `is_default_phone` (plus de `is_default` ambigu). Migration **100** migre les anciennes lignes puis supprime `is_default`.
- **`jurisdiction_policy_settings`** : `jurisdiction_code` unique, `inherit_phone_countries_from_residence` (défaut `false`), `default_residence_iso2` / `default_phone_iso2` nullable (FK vers `country_directory`), `updated_at`.

Fichier migration : `api/alembic/versions/100_jurisdiction_policy_settings_split_defaults.py`.

## Admin Navigation Changes

- Page **`/admin/registration`** : raccourcis vers **Jurisdiction Policies**, **Country Directory**, **Field Definitions**, **Sessions** ; sur chaque carte flow : encart **jurisdiction policy** (compteurs, défaut téléphone, badge héritage) + bouton **Edit jurisdiction policy**.
- Liste flows : paramètre `include_policy_summary` côté API (défaut `true`) pour joindre le résumé sans N+1.

## Jurisdiction Policies Pages

- **`/admin/jurisdiction-policies`** : cartes par juridiction (compteurs, défauts, héritage).
- **`/admin/jurisdiction-policies/[code]`** : résumé, **settings** (toggle héritage, sélecteurs de défauts), **presets** (`eu_explicit`, `eu_from_directory`, `uae_explicit`, `mirror_phone_to_residence`, `apply_residence_to_phone`, `clear`), **tableau pays** (toggles résidence / téléphone, radios défauts, sauvegarde PATCH).
- **`/admin/country-directory`** : tableau **lecture seule** du référentiel.

## Backend API

| Méthode | Chemin | Rôle |
|--------|--------|------|
| GET | `/api/admin/jurisdiction-policies` | Liste juridictions + agrégats |
| GET | `/api/admin/jurisdiction-policies/{code}` | Détail (settings + lignes) |
| PATCH | `.../{code}/settings` | Settings globaux |
| PATCH | `.../{code}/countries` | Remplacement complet des lignes (validations défauts uniques, ISO connus) |
| POST | `.../{code}/apply-preset` | Presets serveur explicites |
| GET | `/api/admin/country-directory` | Référentiel pays |
| GET | `/api/admin/jurisdictions/{code}/country-policies` | Compat lecture (legacy) |

Implémentation : `jurisdiction_policy_admin_service.py` + `jurisdiction_policy_admin_router.py`.

## Runtime Integration

- `list_allowed_phone_countries` : si `inherit_phone_countries_from_residence`, les entrées suivent `allow_residence` ; sinon `allow_phone_country_code`.
- `is_phone_country_allowed` : même règle.
- `jurisdiction_has_phone_policies` : en mode héritage, équivalent à la présence de policies résidence.
- Enrichissement : `default_phone_country`, `default_country` (country_picker), listes avec flags `is_default_residence` / `is_default_phone` dans les objets pays.

## Flow Editor Integration

Bloc **« Jurisdiction policy in use »** : code juridiction, compteurs, défauts, lien vers la page détail — **pas d’édition inline** des lignes pays.

## Flutter Consumption

- `registration_flow_screen` : après chargement d’écran, **initialisation** `default_country` / `default_phone_country` dans `_formData` si vide.
- `RegistrationFlowRenderer` : affichage country picker avec repli sur `default_country` dans les props.

## Tests Added / Adapted

- `tests/test_registration_jurisdiction_country_policies.py` : prérequis migration **100**, colonnes défauts scindées, `RegistrationJurisdiction` pour codes de test, **héritage téléphone**, API liste/détail/PATCH rejet double défaut/preset clear, smoke UAE seedé.

Les tests **UI admin** (Playwright) ne sont pas automatisés ici ; la régression repose sur l’API et une vérification manuelle des pages.

## Remaining Gaps / Next Steps

- **Édition du country directory** (activation / noms) : API PATCH + garde-fous.
- **Auth admin** sur les nouveaux endpoints (alignement JWT comme le reste du back-office si requis).
- **Nationalité vs résidence** : si les listes doivent diverger par `binding_slug`, ajouter un axe en base (ex. type de picker ou colonne dédiée).
- **CI** : `alembic upgrade head` pour exécuter les tests policy.
- **Commit dans les tests** : un avertissement SQLAlchemy peut apparaître sur `commit()` dans la session transactionnelle de test ; acceptable ou remplacer par `flush` dans un mode test dédié.
