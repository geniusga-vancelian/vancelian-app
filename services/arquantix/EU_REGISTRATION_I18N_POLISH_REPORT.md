# EU Registration Flow v2 — Rapport polish i18n

## Executive summary

Les libellés du flux **EU Individual Onboarding v2** (`flow_id` fixe `c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f`) ont été harmonisés pour un ton **clair, premium et rassurant**, avec une base **anglais + français** structurée pour extension future.

- **Migration** : `api/alembic/versions/122_eu_registration_flow_v2_i18n_polish.py` (revises `121`).
- **Structure inchangée** : `step_key`, `screen_key`, `component_type`, `binding_slug`, ordre des étapes, logique métier.
- **Champs mis à jour** : titres / descriptions d’étapes (`title`, `description`, `title_i18n`, `description_i18n`), titres / sous-titres d’écrans (`title_i18n`, `subtitle_i18n`), `config_json.step_metadata` (descriptions localisées `en`/`fr` où pertinent), `props_json` des composants (labels, placeholders, textes légaux, checkboxes).

## Principes de microcopy retenus

- Phrases courtes, vocabulaire simple, ton professionnel sans jargon compliance inutile.
- Cohérence d’un écran à l’autre (« vous », transparence sur l’usage des données).
- Email OTP optionnel : expliquer **maintenant ou plus tard**, sans culpabiliser ni sur-promettre.
- Consentements : sérieux et lisibles ; marketing explicitement **optionnel**.

## Écrans / champs modifiés

| Étape (`step_key`) | Changements principaux |
|-------------------|-------------------------|
| `identity` | Titre « Your legal name » ; sous-titre sur alignement ID ; placeholders prénom/nom discrets (Alex / Dupont). |
| `date_of_birth` | Mise en avant « eligibility only ». |
| `residence_country` | « Where you live » + rôle fiscal/réglementaire sans lourdellé. |
| `home_address` | `address_step` : titres / libellé de recherche en en/fr ; sous-titre sur saisie progressive. |
| `contact_email` | Focus notifications compte, pas spam. |
| `email_verification_optional` | Bloc intro réécrit ; code « 6-digit » ; case à cocher « I’ll verify later » + explication réglages. |
| `terms` | Texte d’intro + cases conformité reformulées ; marketing optionnel explicite. |

## Avant / après (extraits)

- **Email OTP (legal_content)** : passage d’un ton procédural (« If you received… ») à un ton rassurant (continuer maintenant, vérifier plus tard dans le profil).
- **Terms** : « I accept… » → « I have read and accept… » + mention explicite de la protection des données.
- **Marketing** : « marketing communications (optional) » → « Send me occasional product updates and news (optional) ».

## Textes hors DB / runtime Flutter

- Les clés **`step_metadata.description`** peuvent être des objets `{en, fr}` dans `config_json` : **le moteur d’API résout `title` / `subtitle` / `props` des composants**, mais **`config_json` n’est pas passé par `resolve_localized_props`** côté sérialisation standard du flux. Les clients qui afficheraient `config_json` brut devraient résoudre les locales eux-mêmes (non vérifié sur l’app mobile).
- **`legal_content`** : le renderer Flutter lit `text` ou `content` en **String** après résolution API ; les dicts sont aplatis côté backend via `resolve_localized_props`.
- **Titres d’étape « page »** : si l’app utilise un titre **hardcodé** par route au lieu des champs API, il resterait hors DB (à vérifier dans les écrans Flutter d’onboarding).

## Recommandations i18n futures

- Ajouter `de`, `it`, etc. en dupliquant les clés dans les maps `*_i18n` et dans les props localisées.
- Vérifier la **gouvernance** registration (`_check_i18n`) : les labels en dict `en`/`fr` satisfont les contrôles sur les champs connus.
- Centraliser un **glossaire** produit (email, résidence, adresse) pour éviter les dérives entre flux.

## Fichiers impactés

- `api/alembic/versions/122_eu_registration_flow_v2_i18n_polish.py`
