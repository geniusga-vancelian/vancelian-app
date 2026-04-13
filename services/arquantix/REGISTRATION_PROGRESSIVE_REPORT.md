# Registration progressive — rapport d’implémentation

## Objectif

Parcours d’inscription **robuste** : progression et prochaine étape **dérivées** de `profile_json.collected`, reprise **alignée** sur ces données (sans s’appuyer sur le curseur session pour la vérité UX), module **Home** premium (titre, description, %, prochaine étape, CTA).

## 1. Logique dérivée (source unique : `collected`)

Module : `api/services/registration_progress_derived.py` (hors package `registration` pour éviter les imports circulaires).

- **12 jalons canoniques** (ordre fixe, aligné sur le ratio registration admin) :  
  `identity` → … → `financial_acknowledgements`.
- **`compute_registration_progress_from_collected(collected)`** → ratio 0..1, % 0..100, complétés / total (ex. 3/12 → 25 %).
- **`compute_next_registration_step_from_collected(collected)`** → premier jalon incomplet `(clé, libellé FR)` ou `None` si tout est complété.
- **`build_derived_registration_progress`** → texte de reprise pour le dashboard.

Les prédicats reprennent la même sémantique que `registration_progress.py` (nom, adresse, emploi conditionnel, etc.) mais **sans** lecture DB.

## 2. API profil mobile

`build_mobile_profile_dict` expose en plus :

- `registration_derived_completion_ratio`, `registration_derived_progress_percent`
- `registration_derived_next_step_key`, `registration_derived_next_step_label`
- `registration_derived_resume_description`
- `registration_derived_completed_count`, `registration_derived_total_count`

Schéma : `MobileAppProfileResponse` (`services/test_clients/schemas.py`).

Les champs **session** (`registration_session_*`) restent informatifs mais ne pilotent plus la barre Home (priorité au dérivé côté Flutter).

## 3. Reprise runtime (recalage curseur)

`RegistrationSessionService._realign_session_cursor_from_collected` :

- Lit `person.profile_json["collected"]`.
- Calcule la **prochaine clé canonique** incomplet.
- Résout l’écran cible : **`screen_key`** (ex. `identity_form`) pour flux EU v4 **ou** `step_key` égal à la clé (flux v3).
- Met à jour `current_step_id`, `current_screen_id`, `progress_percent` (dérivé), puis `expire` la session pour recharger les relations.

Appelé après **reprise** `start_session`, après **création** si `person_id` présent, et à chaque **`get_current_screen`**.

## 4. Application Flutter

- **`MobileAppProfile`** : nouveaux champs ; `registrationProgressDisplayPercent` préfère **`registration_derived_progress_percent`** ; `registrationResumeDescriptionDisplay` pour le texte carte.
- **`RegistrationProgressModule`** + **`RegistrationProgressModuleBuilder`** (`features/registration/widgets/registration_progress_module.dart`, `registration_progress_module_builder.dart`) : module **unique** (anneau circulaire, titre *Finalisez votre inscription*, sous-titre juridiction / flux / prochaine étape dérivée, CTA **Continuer**, liste des étapes avec statuts) — alimenté par le profil (`registration_derived_*`) et les étapes du **flux actif** (`GET …/current-jurisdiction` + `GET …/flows/active`). Réutilisé par **`RegistrationFlowLauncherScreen`** (page *Parcours d’inscription*) et par **`HomeScreen`** lorsque `shouldShowRegistrationResume` (compte PARTIAL / progression incomplète). L’ancienne **`RegistrationResumeCard`** (barre linéaire, variante header sombre) a été **supprimée** pour éviter deux UX concurrentes.
- **`RegistrationFlowStepInfo`** : parsing des `steps` du JSON flux actif (même source que le launcher).
- **`RegistrationFlowLauncherScreen`** : hub Profil avec **profil réel** (`ProfileIdentityCoordinator`) + métadonnées flux API ; `typedef RegistrationTestLauncherScreen` conservé pour les tests.

### 4.1 Différences page Registration vs Home

| Aspect | Launcher (page complète) | Home (dashboard) |
|--------|-------------------------|------------------|
| Conteneur | `Scaffold` + AppBar *Parcours d’inscription*, scroll, erreurs fatales, états vides, bouton **Rafraîchir** | Bloc dans la liste du dashboard, marges `DashboardLayoutConstants` |
| Données | Chargement local à l’écran (`RegistrationApi` sans resolver explicite dans le code historique) | Même builder après `refreshDisplayIdentity` : `RegistrationApi` avec **`accessTokenResolver`** pour les appels authentifiés |
| Erreur chargement module | Bandeau + états vides dans la page | Bandeau erreur + CTA **Continuer** (repli sur `jurisdiction` profil) |

## 5. UX Home

Module **identique** au hub (pas la carte simplifiée) si `shouldShowRegistrationResume` : progression dérivée + liste des sections du flux, même hiérarchie visuelle que `SetupProgressCard`.

## 6. Tests

- `tests/test_registration_progress_derived.py` : cas vide, milieu de parcours, tout complété.
- `tests/test_mobile_identity_security.py` : égalité `/api/app/profile` vs `/api/mobile/flutter/profile`.

Scénarios manuels recommandés : abandon par étape, réouverture, logout/login, vérification des champs préremplis via réponses `start_session` / `get_current_screen` (données projetées dans le contexte).

## 7. Limitations

- Les **12 jalons** doivent rester alignés avec les **écrans** `screen_key` du flux actif (EU v4 : mapping explicite dans `CANONICAL_KEY_TO_SCREEN_KEY`).
- Si la juridiction utilise un flux sans ces écrans, le recalage log un warning et **ne** déplace pas le curseur.
- Hors champ `collected` (ex. téléphone vérifié côté 2FA uniquement) : la progression macro reste dans `compute_canonical_registration_progress` (non dupliquée ici).

## 8. Fichiers principaux

| Zone | Fichiers |
|------|----------|
| Dérivé | `api/services/registration_progress_derived.py` |
| Session | `api/services/registration/service.py` (`_realign_session_cursor_from_collected`, …) |
| Profil API | `api/services/test_clients/mobile_profile.py`, `schemas.py` |
| Flutter | `mobile/lib/features/profile/data/mobile_app_profile.dart`, `registration_progress_module.dart`, `registration_progress_module_builder.dart`, `registration_flow_step_info.dart`, `registration_flow_launcher_screen.dart`, `home_screen.dart` |

## 9. UX conversion (niveau supérieur)

### Modal « reprise douce »

- **Quand** : `client_status == PARTIAL` **et** progression déjà entamée (`% > 0` ou jalons complétés `> 0`).
- **Quoi** : feuille DS `Modale` — *« Reprendre votre inscription ? »*, résumé (% complété, étape suivante, étapes restantes), **Continuer** (ouvre le flux), **Plus tard** (ferme).
- **Fréquence** : une fois par cycle d’identité (`SessionIdentityContext.epoch`) via `RegistrationResumePromptGate` — pas de spam à chaque retour Home après fermeture.
- **Fichiers** : `mobile/lib/core/registration_resume_prompt_gate.dart`, `home_screen.dart` (`_tryShowRegistrationResumeSoftPrompt`).

### Module Home (levier complétion)

Aligné sur le hub **Parcours d’inscription** : `RegistrationProgressModule` (anneau, sous-titre juridiction + flux + prochaine étape dérivée, liste des étapes API, CTA). Chargement via les mêmes endpoints que le launcher après `GET /profile` (identité affichée).

## 10. Parcours d’activation élargi (Home)

Depuis l’élargissement **activation journey** (3 macro-étapes : vérification compte, premier dépôt, premier investissement), le détail produit, les données et le repli API legacy sont documentés dans **`ACTIVATION_JOURNEY_REPORT.md`**. Tant que le backend expose `activation_journey`, la Home préfère **`ActivationJourneyHomeModule`** ; sinon repli sur `RegistrationProgressModule` + `shouldShowRegistrationResume` comme avant.

## 11. Validation (manuelle recommandée)

1. Compte **PARTIAL** sur Home → module visible (anneau + étapes + Continuer).
2. Compte **ACTIVE** (ou `shouldShowRegistrationResume` faux) → module absent.
3. **Continuer** depuis Home → `RegistrationFlowScreen` avec juridiction résolue (API ou repli profil).
4. Tap sur une **ligne d’étape** → même navigation que Continuer.
5. **Profil → Parcours d’inscription** : même composant sous-jacent ; page entière conserve AppBar, rafraîchir, messages d’erreur.
