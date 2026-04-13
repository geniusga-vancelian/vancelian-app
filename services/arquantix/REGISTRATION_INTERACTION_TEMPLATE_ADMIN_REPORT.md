# Registration — templates d’écran interaction (admin)

## Executive Summary

Le **Registration Builder** admin s’appuie sur un **registre de templates métier** côté backend (`interaction_templates.py`) exposé via **`GET /api/admin/registration/interaction-templates`**. Les écrans **`screen_type=interaction`** sont **validés strictement** à la création et au patch (type + `interaction_config_json` obligatoires pour le SMS ; les formulaires ne peuvent pas porter de champs d’interaction). Le runtime Flutter / API publique **ne change pas** : il continue à lire `screen_type`, `interaction_type`, `interaction_config_json`. Les clés **`interaction_template_key`** et **`interaction_template_display_name`** sont **déduites** à la sérialisation admin (pas de colonne DB, compatibilité totale avec l’existant).

## Interaction Template Registry

Fichier : `api/services/registration/interaction_templates.py`.

| template_key | display_name | interaction_type | selectable | Notes |
|--------------|--------------|------------------|------------|--------|
| `confirmation_code_sms` | Confirmation code (SMS) | `phone_verification_sms` | oui | Aligné sur le runtime 2FA / registration actuel. |
| `confirmation_code_email` | Confirmation code (email) | `email_verification_otp` | non (soon) | Ossature : pas de création admin via ce type tant que le runtime ne le supporte pas (422 si tentative). |

Chaque template expose : `default_title`, `default_subtitle`, `default_button_label`, `default_interaction_config`, `required_config_fields`, `description`.

## Admin Builder UX Changes

- **Ajout d’écran** : boutons **« + Form screen »** (prompt titre) et **« + Code SMS »** (POST avec le preset SMS).
- **Édition** : pour **Interaction screen**, liste **Interaction template** (presets + **Custom (advanced)**) qui préremplit titre, sous-titre, bouton, `interaction_type` et slugs 2FA ; l’admin peut toujours les modifier.
- **Liste des screens** : badge **interaction**, libellé métier si inféré (**Confirmation code (SMS)**), et `interaction_type` en sous-texte discret.

## Backend Validation

- **`screen_type=form`** : `interaction_type` vide et pas de `interaction_config_json` non vide.
- **`screen_type=interaction`** : `interaction_type` et `interaction_config_json` (objet) obligatoires.
- **`phone_verification_sms`** : `source_field_slug`, `verified_flag_slug`, `purpose` non vides dans la config.
- **Autres `interaction_type`** : **422** avec message explicite (seul le SMS est supporté par le runtime aujourd’hui).

Lors d’un **PATCH** vers `form`, les champs d’interaction sont **effacés** en base après validation.

## Compatibility Notes

- Aucune migration : pas de `interaction_template_key` stocké ; **inférence** par `(interaction_type + présence des champs requis dans la config)`.
- Écrans interaction **déjà en base** qui matchent le preset SMS reçoivent `interaction_template_key: confirmation_code_sms` dans les réponses admin.
- Runtime (`runtime_router`, Flutter) : **inchangé**.

## Tests Added

Fichier `api/tests/test_registration_interaction_templates_admin.py` :

- Liste des templates (SMS sélectionnable, email squelette non sélectionnable).
- Création interaction SMS complète → 201 + `interaction_template_*` renseignés.
- Config incomplète → 422.
- Form + `interaction_type` → 422.
- Type `email_verification_otp` → 422 (non supporté runtime).
- Écran legacy en base → inférence du template en GET liste.
- PATCH `screen_type: form` → interaction effacée.

**Tests UI admin** : non automatisés ici (Next.js) ; comportement vérifié dans `flows/[id]/edit/page.tsx`.

## Remaining Gaps / Next Steps

- Activer **`confirmation_code_email`** : implémenter le chemin runtime + retirer `selectable: false` + étendre la validation admin.
- Tests E2E Playwright optionnels sur le builder.
- Gouvernance / health du flow : avertissements si un template « soon » apparaît en base (actuellement impossible via API).
