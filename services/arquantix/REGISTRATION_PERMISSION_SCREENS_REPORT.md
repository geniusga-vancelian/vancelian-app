# Rapport : écrans permission (notifications / Face ID) — inscription

## Objectif

Introduire des écrans d’activation **notifications push** et **Face ID** dans le parcours d’inscription, pilotés par le backend (`screen_type: permission_prompt`), rendus dans l’app Flutter avec le design system (`DsPermissionPromptLayout`), configurables dans l’admin « Registration flow editor », avec un raccourci contextuel depuis l’admin **Juridiction** (policies).

## Modèle métier (contrat API)

- **`screen_type`** : `permission_prompt`.
- **`config_json`** (obligatoire côté validation admin) :
  - `permission_kind` : `face_id` ou `push_notifications`
  - `decision_slug` : slug booléen enregistré à `true` (bouton principal) ou `false` (bouton secondaire)
  - `secondary_button_label` : libellé du refus (optionnel côté UX, défauts dans les templates)
- Pas d’`interaction_type` ni d’`interaction_config_json` pour ce type d’écran.

Les presets exposés par l’API sont définis dans `api/services/registration/permission_prompt.py` (`list_permission_prompt_templates_for_api`) : `face_id_activation` et `push_notifications_activation` avec `decision_slug` respectivement `face_id_enabled` et `push_notifications_enabled`.

## Backend (déjà en place dans le dépôt)

Fichiers et rôles principaux :

- `api/services/registration/permission_prompt.py` — parsing, validation admin, liste des templates.
- `api/services/registration/interaction_helpers.py` — `effective_screen_type` inclut `permission_prompt`.
- `api/services/registration/service.py` — sérialisation du flow, blocage/soumission avec booléen requis sur `decision_slug`.
- `api/services/registration/admin_router.py` — `GET /api/admin/registration/permission-prompt-templates`, création/mise à jour d’écran avec `validate_screen_for_admin`.
- `api/services/registration/governance.py` — pas d’alerte « écran vide » pour `permission_prompt` sans composants.

Aucune modification supplémentaire du backend n’a été nécessaire pour finaliser cette itération.

## Flutter

### Modèle (`registration_models.dart`)

- Getters : `isPermissionPromptScreen`, `permissionKind`, `permissionDecisionSlug`, `permissionSecondaryButtonLabel` (défaut « Not Now » si absent).
- Ajustement mineur sur `permissionSecondaryButtonLabel` pour éviter l’usage de `config!` après test null.

### Écran de flux (`registration_flow_screen.dart`)

- Détection `screenType == 'permission_prompt'` : rendu dédié avec `DsPermissionPromptLayout` + `DsPermissionHero` (icône notifications si `permission_kind == push_notifications`, sinon symbole Face ID du DS).
- `submitScreen` avec corps `{ decision_slug: true|false }` selon le bouton.
- Fond `AppColors.iosChromeBackground`, titre du `AppTopNavBar` masqué sur cet écran (titre porté par le layout).
- CTA bas fixe masqué (`_buildBottomCta` → `SizedBox.shrink`) pour éviter le double bouton « Continue ».
- `_allRequiredFilled` retourne `true` pour cet écran (pas de champs formulaire).
- Clé de transition enrichie pour forcer l’animation lors du changement de type d’écran.

## Admin web — éditeur de flux

Fichier : `web/src/app/admin/registration/flows/[id]/edit/page.tsx`

- Chargement de `GET /api/admin/registration/permission-prompt-templates`.
- Type d’écran **Permission (Face ID / notifications)** dans le sélecteur, avec panneau de configuration (`permission_kind`, `decision_slug`, `secondary_button_label`, liste de presets).
- Boutons rapides dans la liste des écrans d’une étape : **+ Notifications** et **+ Face ID** (`POST` écran avec `screen_type: permission_prompt` et `config_json` issu du template).
- Sauvegarde de la structure : pour `permission_prompt`, envoi d’un `config_json` limité aux trois clés permission (évite de mélanger avec la config « modale téléphone » des formulaires).
- Badges / sous-ligne dans la liste d’écrans pour repérer les écrans `permission_prompt` et le `permission_kind`.
- Section composants : message explicite indiquant que tout passe par les deux boutons et `decision_slug`.

## Admin web — page Juridiction (policies)

Fichier : `web/src/app/admin/jurisdiction-policies/[code]/page.tsx`

- Chargement des juridictions registration + flux, filtrage par `jurisdiction_id` correspondant au `code` de la page.
- Carte **Flux d’inscription (registration)** : liste des flux liés à la juridiction avec lien direct vers `/admin/registration/flows/[id]/edit`, plus texte d’orientation pour ajouter les pages Notifications / Face ID via les boutons de l’éditeur.

## Vérifications recommandées

- Publier un flux contenant un écran `permission_prompt`, démarrer une session test : vérifier que le client reçoit `config.permission_kind` / `decision_slug` et que la soumission avance l’étape.
- `flutter analyze` sur les fichiers registration (dans cet environnement : pas d’erreur bloquante sur les fichiers modifiés ; un avertissement *info* préexistant sur commentaire de library dans `registration_models.dart` peut subsister).

## Fichiers touchés dans cette passe

| Fichier | Changement |
|---------|------------|
| `mobile/lib/features/registration/data/registration_models.dart` | Getter secondaire sans `config!` |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | UI permission + submit booléen + scaffold |
| `web/src/app/admin/registration/flows/[id]/edit/page.tsx` | Type permission, templates, CRUD UI |
| `web/src/app/admin/jurisdiction-policies/[code]/page.tsx` | Carte flux d’inscription + liens édition |
