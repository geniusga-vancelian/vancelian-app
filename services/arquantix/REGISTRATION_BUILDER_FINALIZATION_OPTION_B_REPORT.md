# Registration Builder — finalisation Option B

## Executive Summary

Cette livraison finalise l’**admin Registration Builder** pour un usage quotidien plus propre (publication, règles, i18n visible, liste des flux) **sans** toucher au moteur runtime Flutter ni assouplir le **publish guard**.

Points principaux :

- **Diagnostic centralisé** : `GET /api/admin/registration/flows/health-summary` et `GET /api/admin/registration/flows?include_health=true`.
- **Governance** : les JSON de règles « legacy » (`{"type": "required"}`, etc.) ne génèrent plus de faux avertissements « missing field » ; les objets non-objets sont signalés.
- **UI éditeur de flux** : `validation_rule_json` + `visibility_rule_json` sur les composants via le **RuleEditor** existant (mode simple + JSON) ; résumé `in` / `not_in` lisible ; publication via **modale** (plus de `prompt`) ; panneau Health **groupé par catégorie** avec IDs courts ; **badges i18n** inline (steps / screens / components).
- **Liste des flux** : badges statut, Ready / Blocked, compteurs health.
- **Field definition** : affichage explicite **Required by default** + usages déjà présents.
- **Garde-fou création** : impossible de sauver un **nouveau** client field sans sélection catalogue (aligné API).

---

## Remaining Non-Publishable Flow Diagnosis

### Référence avant correctifs catalogue / bindings (phase précédente)

- Symptôme observé : **1** flux actif bloqué (ex. *EU Individual Onboarding v1*), **6** erreurs de type **field_binding** / composants orphelins, **~64** warnings surtout **i18n** et **rules** bruitées.

### Causes racines traitées (hors de ce diff UI, via migrations catalogue)

- Bindings sans `field_definitions` correspondantes ; composants **field-bound** sans `binding_slug` / `field_definition_id` ; clés auto-générées — corrigé en base (migrations **092** / **093**).

### État après (vérification locale `check_flow_health`)

| Métrique | Valeur |
|----------|--------|
| `flows_total` | 4 |
| `publishable_count` | **4** |
| `blocked_count` | **0** |

Tous les flux passent le publish guard côté données actuelles.

### Nouvel endpoint de diagnostic

`GET /api/admin/registration/flows/health-summary`

Réponse : `flows_total`, `publishable_count`, `blocked_count`, et par flux : `can_publish`, `error_count`, `warning_count`, `errors[]` (détail des bloquants).

---

## Validation Rule UI Added

Fichier : `web/src/app/admin/registration/flows/[id]/edit/page.tsx`

- **RuleEditor** réutilisé pour :
  - **Visibility Rule (component)** — client field et content block.
  - **Validation Rule** — principalement champs saisie.
- Champs supportés en mode simple : **field**, **operator**, **value** / **values** (pour `in` / `not_in`), alignés sur `VALID_RULE_OPERATORS` backend.
- **Résumé** enrichi pour `in` / `not_in` : ex. `country in [FR, BE]`.
- Persistance : `PATCH` / `POST` composants envoient `visibility_rule_json` et `validation_rule_json` (déjà supportés par l’API).

---

## i18n Completeness Inline

- Badges **i18n ✓ / ~ / !** (vert / ambre / rouge) avec **tooltip** sur :
  - **Steps** : `title_i18n` + `description_i18n` si une description est utilisée.
  - **Screens** : `title_i18n` + `subtitle_i18n` si sous-titre présent.
  - **Components** : champs liés (label / placeholder pour inputs ; label + contenu pour blocs).
- Langues : **en** et **fr** (`LANGS`), cohérent avec `SUPPORTED_LANGUAGES` côté API.

---

## Admin UX Polish

### Publish / Archive

- **Publish** : modale (nom obligatoire), désactivée si `health.can_publish === false` ; message de succès sous l’en-tête.
- **Archive** : libellé du bouton de confirmation **Archive** (plus « Delete » générique) ; texte de description clarifié.

### Health panel

- Erreurs **bloquantes** et **warnings** regroupés par **category** ; sous chaque erreur, extraits d’ids (`step` / `screen` / `comp`) pour corrélation manuelle avec la base.

### Flow list

- Appel `GET .../flows?include_health=true`.
- Badges : **Blocked** si `!can_publish`, **N warnings** si publishable avec warnings, **Ready** si publishable sans warnings ; ligne **Health** `err · warn`.

### Field Catalog (builder)

- Bloc catalogue **encadré** (bordure emerald) + texte « recommended ».
- Alerte si création client field sans `_field_definition_id`.
- `binding_slug` en lecture seule pour les **nouveaux** champs (catalogue seule source).

### Field definition detail

- Ligne **Required by default** dans la fiche info.

---

## Health Check Adjustments

Fichier : `api/services/registration/governance.py` — `_validate_rule_json`

| Avant | Après |
|-------|--------|
| Tout JSON sans `operator` implicite → warning « missing field » | Règles **sans** clé `operator` et **sans** `rules` → **ignorées** (legacy Flutter / seeds `type: required`) |
| Type non-dict passait dans la logique operator | **Non-dict** → **warning** explicite « expected a JSON object » |

Aucun assouplissement des erreurs **field_binding**, **structure**, **component**, etc.

---

## Tests Added

| Fichier | Couverture |
|---------|------------|
| `api/tests/test_registration_governance_rules.py` | Legacy validation sans bruit ; non-objet ; règle structurée sans `field` |
| `api/tests/test_registration_api.py` (`TestAdminAPI`) | `flows/health-summary` ; `flows?include_health=true` ; round-trip `validation_rule_json` + `visibility_rule_json` sur composant |

---

## Before / After Publishability

| | Avant (réf. projet, post-seeds problématiques) | Après (DB à jour + governance) |
|--|-----------------------------------------------|--------------------------------|
| Flux **publishables** | **3 / 4** | **4 / 4** |
| Causes bloquantes corrigées | Field defs manquantes, orphelins, clés auto | Catalogue + migrations **092**/**093** + pas de changement au guard |
| Bruit « rules » sur legacy | Oui (warnings massifs) | Réduit (skip shorthand sans `operator`) |

---

## Remaining Gaps Before Phase A

- **Warnings i18n** : toujours nombreux sur les flux seeds tant que `title_i18n` / `label_i18n` ne sont pas remplis — **informatifs**, non bloquants.
- **Navigation Health → entité** : les IDs sont affichés en tronqué ; pas de deep-link automatique vers le bon step/screen dans l’UI (amélioration future).
- **Tests UI** : pas de suite E2E Playwright sur le builder (hors périmètre demandé).
- **Phase A** (Execution Tracking, Audit Trail, Replay) : à traiter dans un chantier séparé.

---

## Fichiers modifiés / ajoutés

- `api/services/registration/governance.py`
- `api/services/registration/admin_router.py`
- `api/tests/test_registration_governance_rules.py` (nouveau)
- `api/tests/test_registration_api.py`
- `web/src/app/admin/registration/flows/[id]/edit/page.tsx`
- `web/src/app/admin/registration/page.tsx`
- `web/src/app/admin/registration/field-definitions/[id]/page.tsx`
- `REGISTRATION_BUILDER_FINALIZATION_OPTION_B_REPORT.md` (ce fichier)
