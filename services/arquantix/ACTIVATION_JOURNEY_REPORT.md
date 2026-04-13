# Parcours d’activation client (Home) — rapport

**Date :** 2026-04-07  
**Dernière mise à jour :** 2026-04-07 (polish wording + transitions + instrumentation funnel)  
**Périmètre :** module Home — perception fluide type Revolut, **sans** effet « montagne KYC » (le poids est porté par la donnée métier, pas par un anneau 1/3 trompeur).

---

## PARTIE 1 — Audit de l’existant (avant changement)

| Question | Réponse |
|----------|---------|
| **Quand le module s’affichait** | `MobileAppProfile.shouldShowRegistrationResume` (repli legacy) ou `activation_journey.show_module`. |
| **Données consommées** | `GET /api/mobile/flutter/profile` → bloc `activation_journey` (+ `registration_*` pour le ratio inscription dans l’étape 1). |
| **Progression** | **v2+** : `weighted_progress_percent` (0–100), pondéré (voir ci‑dessous). Plus d’affichage « 1/3 » pour l’activation. |
| **Où étendre** | `build_activation_journey` ; UI `ActivationJourneyHomeModule` + `ProgressRingPercent`. |

---

## PARTIE 2 — Visibilité

`show_module` est `true` tant qu’au moins une des trois conditions métier manque :

1. **account_verification** — `should_show_registration_resume` (aligné Flutter / admin).
2. **first_deposit** — `has_first_deposit` (custody).
3. **first_investment** — `has_first_investment` (exchange / PE / position crypto).

Quand les trois sont satisfaits : `show_module` = `false`, le gros module disparaît. **v3** : le backend expose en plus `activation_complete: true` et `completion_message` (voir §12) pour un **bandeau discret** sur la Home sans réafficher tout le parcours.

---

## PARTIE 3 — Modèle dynamique des étapes (v3)

`config_version` : **3**.

Chaque entrée de `stages[]` expose :

| Champ | Rôle |
|-------|------|
| `key` / `id` | `account_verification`, `first_deposit`, `first_investment`. |
| `status` | `completed` \| `available` \| `in_progress` \| `locked` (voir §3 bis). |
| `weight` | `0.7` / `0.2` / `0.1` — contribution à la **barre globale**. |
| `is_next_step` | `true` sur **une** seule étape (prochaine action). |
| `title`, `subtitle`, `cta_label`, `target_route` | Contenu serveur (évolutif admin). |

Champs **racine** du bloc :

| Champ | Rôle |
|-------|------|
| `weighted_progress_percent` | 0–100, calcul pondéré (voir §4). |
| `headline` | Titre hero (voir **§12 — wording final**). |
| `hero_subtitle` | Sous-titre motivation (§12). |
| `remaining_steps_message` | Reliquat d’étapes (§12). |
| `primary_cta_label` / `primary_cta_target_route` | CTA principal = **prochaine** étape (§12). |
| `activation_complete` | `true` si les trois étapes sont terminées. |
| `completion_message` | Libellé de clôture (§12) quand `activation_complete`. |

### §3 bis — Règles d’émission des statuts (v3)

Parcours **linéaire** : `next_idx` = première étape non satisfaite (0 → 1 → 2).

| Statut | Condition |
|--------|-----------|
| **completed** | L’étape est satisfaite (compte OK / dépôt OK / invest OK). |
| **locked** | Index **strictement supérieur** à `next_idx` : prérequis manquants (ex. dépôt et invest tant que le compte n’est pas validé). |
| **available** | `index == next_idx` et l’étape n’est pas complétée, **sauf** le cas « inscription partielle » ci‑dessous : typiquement **premier dépôt** ou **premier invest** prêts à être lancés ; ou **vérification compte** avec **0 %** d’avancement (pas encore entamée). |
| **in_progress** | Uniquement **étape 1 (account_verification)** : inscription considérée incomplète **et** ratio d’inscription **strictement entre 0 et 1**, **ou** ratio ≥ 1 mais le moteur considère encore le parcours incomplet (cas limite). |

Exemples :

- Compte incomplet → `first_deposit` et `first_investment` : **locked**.
- Compte OK, pas de dépôt → `first_deposit` : **available**, `first_investment` : **locked**.
- Dépôt OK, pas d’invest → `first_investment` : **available**.

---

## PARTIE 4 — Progression intelligente (pondération)

Poids :

| Étape | Poids |
|-------|-------|
| account_verification | **0.7** |
| first_deposit | **0.2** |
| first_investment | **0.1** |

**Formule** (0–100 %) :

- Si la vérification compte **n’est pas** terminée :  
  `weighted = 0.7 × registration_ratio`  
  où `registration_ratio` est dérivé du **moteur d’inscription** (`registration_derived_completion_ratio`, `registration_derived_progress_percent/100`, ou `registration_completion_ratio` en repli).
- Si la vérification est **terminée** :  
  `weighted = 0.7`  
  puis `+ 0.2` si dépôt fait, `+ 0.1` si investissement fait.

Effet produit : **perception de progression rapide** dès que le profil avance (partie 0–70 %), puis paliers **70 % → 90 % → 100 %** sans afficher un « 1/3 » qui sur-représente le KYC.

---

## PARTIE 5 — Étape 1 — Vérification

- Même logique que **`should_show_registration_resume`**.
- Sous-titre dynamique : jalons « Déjà X % » et libellé de prochaine étape (séparateur « · ») lorsque l’étape n’est pas close ; texte par défaut : voir **§12**.
- **CTA principal** (next = étape 1) : **§12**.

---

## PARTIE 6 — Étape 2 — Premier dépôt

- `has_first_deposit` (custody).
- **CTA principal** si next : **§12**.

---

## PARTIE 7 — Étape 3 — Premier investissement

- `has_first_investment`.
- **CTA principal** si next : **§12**.

---

## PARTIE 8 — UX & mapping données → UI (Flutter)

| Donnée API | Rendu |
|------------|--------|
| `weighted_progress_percent` | Anneau **`ProgressRingPercent`** dans un **`AnimatedSwitcher`** (fondu + léger scale) quand le % change ; clé sur le % pour un rendu net à chaque palier. |
| `headline` / `hero_subtitle` / `remaining_steps_message` | Bloc hero dans **`AnimatedSwitcher`** (400 ms) quand titre, sous-titre, CTA ou % changent — perception nette des transitions **vérification → dépôt → invest**. |
| `primary_cta_*` | Un seul bouton principal aligné sur la **next step**. |
| `stages[].status` + `is_next_step` | **ListItem** : **completed** (check vert), **in_progress** (anneau + icône), **available** (fond indigo léger, icône valorisée, **cliquable**), **locked** (cadenas gris, texte atténué, **non cliquable**). |
| `is_next_step` | **Highlight** (fond, bordure, ombre ; durées 280 ms / 340 ms sur le contenu de ligne). |
| `activation_complete` + `completion_message` | Si `show_module` est false : bandeau **`ActivationJourneyCompletionStrip`** (succès discret) sur la Home. |

Aucune donnée de conversion **hardcodée** côté Flutter pour les libellés métier : ils viennent du JSON (repli parsing legacy `pending` → `in_progress`).

**Transitions (validées en conception)** : le retour sur la Home après action (pull-to-refresh ou cycle de vie) recharge le profil : le **%**, le **CTA**, le **hero** et les **icônes d’étape** changent ensemble ; l’**AnimatedSwitcher** sur l’anneau et le bloc texte renforce la lisibilité entre **vérification → dépôt**, **dépôt → invest**, puis **invest → bandeau de fin** (module masqué + `completion_message`).

---

## PARTIE 9 — Next step & conversion attendue

**Règle** : première étape non satisfaite dans l’ordre `1 → 2 → 3`.

- Next = **1** si inscription non complète ; sinon **2** si pas de dépôt ; sinon **3** si pas d’investissement.

**Impact conversion attendu** :

- **Clarté** : un seul CTA principal explicite par étape du funnel.
- **Motivation** : % pondéré + message du type « Encore n étapes » / « Une dernière étape » réduit l’effet « montagne ».
- **Confiance** : **available** vs **locked** reflètent l’accessibilité réelle des étapes.

---

## PARTIE 10 — Admin (future-ready)

- `config_version` + champs texte côté serveur : prêts pour surcharge CMS (titres, sous-titres, ordre).
- Règles de complétion et pondération **restent** dans `build_activation_journey`.

---

## PARTIE 11 — Fichiers principaux

| Zone | Fichiers |
|------|----------|
| Métier | `api/services/activation_journey/build.py`, `resume_logic.py`, `signals.py` |
| API | `api/services/test_clients/schemas.py`, `mobile_profile.py` |
| Tests | `api/tests/test_activation_journey.py`, `mobile/test/features/activation/activation_journey_models_test.dart` |
| Flutter | `mobile/lib/features/activation/…`, `setup_progress_card.dart` (`ProgressRingPercent`), `mobile_app_profile.dart`, `home_screen.dart` |

---

## PARTIE 12 — Wording final (polish)

Ton visé : **premium**, **clair**, **motivant**, **non administratif**. Textes émis par `build_activation_journey` (source de vérité API).

| Champ / usage | Texte |
|-----------------|--------|
| `headline` | Trois étapes pour investir en toute confiance |
| `hero_subtitle` | Simple, rapide, sans friction — tout est prêt pour la suite. |
| `remaining_steps_message` (3 restantes) | Encore trois étapes |
| (2 restantes) | Encore deux étapes |
| (1 restante) | Une dernière étape |
| `completion_message` | Tout est en place |
| Titre étape 1 | Sécuriser votre profil |
| Titre étape 2 | Alimenter votre compte |
| Titre étape 3 | Votre premier investissement |
| Sous-titre étape 1 (défaut) | Quelques informations suffisent pour sécuriser votre profil. |
| Sous-titre étape 2 (défaut) | Un versement pour ouvrir l’investissement. |
| Sous-titre étape 3 (défaut) | Faites fructifier votre épargne en quelques gestes. |
| CTA principal next = 1 | Continuer votre profil |
| CTA principal next = 2 | Alimenter mon compte |
| CTA principal next = 3 | Investir maintenant |
| CTA ligne étape terminée | C’est fait |

---

## PARTIE 13 — Transitions visuelles (récap)

| Transition | Comportement UI |
|------------|-----------------|
| **Vérification → dépôt** | % passe vers **70** (palier compte), highlight + icône sur **Alimenter**, CTA principal aligné ; hero et anneau animés (`AnimatedSwitcher`). |
| **Dépôt → invest** | % vers **90**, même mécanisme pour **Investir**. |
| **Invest → fin** | % **100**, puis `show_module` false : le module disparaît ; bandeau **Tout est en place** si `completion_message` présent. |

Les événements **`activation_step_completed`** / **`activation_journey_completed`** (§14) confirment côté logs (debug) que le profil a bien reflété le passage d’étape après rafraîchissement.

---

## PARTIE 14 — Instrumentation funnel (Flutter)

Fichier : `mobile/lib/features/activation/analytics/activation_journey_funnel_events.dart`.

| Événement | Quand | Payload (sans PII) |
|-----------|--------|---------------------|
| `activation_step_viewed` | Affichage du module ; **next step** change (`ActivationJourneyExposure`) | `step_key` : `account_verification` \| `first_deposit` \| `first_investment` |
| `activation_step_clicked` | Tap sur CTA principal ou ligne d’étape débloquée | `step_key`, `target_route` |
| `activation_step_completed` | Après `GET /profile` : une étape passe à **completed** (diff avec l’instantané précédent) | `step_key` |
| `activation_journey_completed` | Même diff : `activation_complete` passe de false à true | _(vide)_ |

Émission : **`debugPrint`** préfixé `[funnel]` en **debug uniquement** — prêt à brancher un backend analytics (même principe que `PostAuthFlowSecurityEvents`).

---

## Synthèse

- **v3** : quatre états UX distincts (**completed**, **available**, **in_progress**, **locked**), fin de parcours signalée par **`activation_complete`** + **`completion_message`**, module principal masqué quand tout est fait, bandeau discret de clôture.
- **Backend** : source de vérité (wording §12) ; **Flutter** : animations ciblées (§8, §13), **funnel** §14.
