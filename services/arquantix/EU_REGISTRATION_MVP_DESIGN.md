# Conception — Registration EU MVP (Arquantix)

**Document :** cadrage produit + technique pour finaliser le MVP sans implémentation lourde immédiate.  
**Références :** `EU_REGISTRATION_AUDIT_REPORT.md`, code existant (registration engine, `registration_progress`, Flutter `RegistrationFlowScreen`).  
**Date :** 2026-04-03

---

## 1. Executive summary

### Décision de source de vérité

| Domaine | Source de vérité canonique (MVP) |
|-----------|-----------------------------------|
| **Ordre des étapes, écrans, composants, validation métier du parcours registration** | **Registration engine** — données en DB (`registration_flows` → steps → screens → components) + runtime `RegistrationSessionService` |
| **Réponses utilisateur pendant le parcours** | `registration_session_data` (+ flags interaction dans la même session) |
| **Identité client enrichie après complétion** | `persons.profile_json` (`collected` / `compliance` selon projection actuelle) |
| **Progression « lifecycle » au-delà du formulaire** (KYC, PE, compte actif) | **Dérivée** — `person.kyc_status`, `pe_clients`, sessions registration ; exposée via un **modèle canonique unique** (voir §5), pas via l’onboarding engine |

### Périmètre exact du MVP

**Inclus**

- Parcours **EU** (`jurisdiction_code = EU`) piloté par le registration engine, **une version de flow active** figée pour la session (comportement déjà assuré par `flow_version`).
- Collecte des données déjà prévues par le seed **085** (5 steps : `basic_info`, `residence`, `professional`, `risk_screening`, `consent`), avec ajustements mineurs listés en §3 (ex. étape OTP intégrée au flow).
- Vérification **SMS** du mobile via mécanisme **`interaction` / `phone_verification_sms`** déjà supporté par le backend et Flutter.
- **Projection** à la fin : `POST .../complete` → `Person` ; alignement du **stade** affiché admin / futur dashboard sur le modèle canonique (§5).
- **Reprise de session** : spifiée en §8 (Phase B) — conception prête, implémentation hors « gros bloc » immédiat.

**Exclu du MVP registration (hors moteur dupliqué)**

- Parcours parallèle dans **l’onboarding engine** (`jurisdiction_configs` + `/api/persons/{id}/onboarding/...`) pour la même collecte registration EU.
- **IDV documentaire** (upload, fournisseur type Sumsub) : hors registration MVP ; peut démarrer **après** completion avec `kyc_status` approprié.
- Création **automatique** d’un `pe_client` **dans** `complete_session` : **option** de Phase C ; le MVP peut s’arrêter à `Person` + `kyc_pending` si l’arbitrage produit le valide.
- Lien **User auth ↔ Person** : dépend du module d’auth global ; le MVP documente les **points de branchement** sans imposer un schéma non encore présent dans le code.

---

## 2. Registration engine target choice

### Base unique : registration engine

**Oui** — le **registration engine actuel** reste la **seule** base pour le parcours EU MVP (collecte, navigation, validation, interaction SMS, completion, audit `registration_execution_events`).

### Rôle de l’onboarding engine (existant)

- Fichiers : `onboarding_engine.py`, routes `services/onboarding/routes.py`, configs `jurisdiction_configs`.
- Aujourd’hui : moteur **séparé** basé sur `profile_json` et des steps dans `config_json` ; **auth non câblée** (TODO dans le code).

**Recommandation MVP**

| Option | Recommandation |
|--------|----------------|
| Utiliser l’onboarding engine pour la registration EU | **Non** — évite duplication et conflit de « vérité » sur les mêmes champs. |
| Désactiver / supprimer l’onboarding engine | **Non** dans le MVP design — peut servir plus tard à un **autre purpose** (ex. « product onboarding » post-login, réinvestissement, paramètres réglementaires) **si** clairement renommé et isolé. |
| Action immédiate | **Geler** tout usage produit de `/api/persons/.../onboarding/...` pour le parcours **première inscription EU** ; documenter que la **registration** = registration engine uniquement. |

### Synthèse

> **Registration EU MVP = registration engine only.**  
> L’onboarding engine reste du legacy / futur usage avec `purpose` ≠ `registration` et avec auth corrigée — hors périmètre MVP EU.

---

## 3. Final target flow for EU MVP

**Alignement de référence :** migration `085_seed_registration_flows.py` — juridiction **EU**, 5 `step_key` listés ci-dessous.  
**Ajustement MVP clé :** insérer **explicitement** une étape (ou un écran) de **vérification SMS** après saisie du numéro — voir §4.

### Ordre recommandé des étapes

| # | Nom (`step_key`) | Objectif |
|---|------------------|----------|
| 1 | `basic_info` | Identité civile + contact + naissance |
| 2 | `phone_verification` *(nouveau step dédié, ou écran interaction dans le step 1 — voir §4)* | Prouver la possession du mobile |
| 3 | `residence` | Adresse + pays + nationalité |
| 4 | `professional` | Emploi, revenus, source of funds |
| 5 | `risk_screening` | Expérience, actifs, tolérance au risque |
| 6 | `consent` | CGU / données / marketing |

*Si le produit préfère **5 steps** au lieu de 6 : fusionner `phone_verification` comme **2ᵉ écran** du step `basic_info` (toujours dans le même flow DB). La logique reste identique ; seul le découpage « step » change.*

---

### Étape 1 — `basic_info`

| Aspect | Contenu |
|--------|---------|
| **Objectif** | Collecter identité et moyen de contact sans exiger encore la preuve SMS (selon stratégie §4, le OTP peut suivre immédiatement). |
| **Données collectées** | `first_name`, `last_name`, `email`, `phone_number` (binding du seed), `date_of_birth` — **tels que déjà dans 085**. |
| **Validations** | Règles composant + `policy_scope` téléphone sur `phone_number` ; date de naissance requise ; **renforcement email** recommandé (Phase A/B backend — voir §9). |
| **Dépendances** | Aucune ; premier step après `startSession`. |
| **Existe déjà** | Oui — seed 085, renderer Flutter. |
| **Ajustements** | Si OTP est **écran séparé** : retirer l’exigence de « phone verified » pour avancer (actuellement le submit avance après validation format) ; l’écran interaction porte la preuve. Si OTP **dans la foulée** : pas de changement de slugs. |

---

### Étape 2 — Vérification téléphone (SMS)

| Aspect | Contenu |
|--------|---------|
| **Objectif** | Vérifier le numéro via OTP (réutilisation du pipeline `interaction` + `RegistrationPhoneSmsOtpPanel`). |
| **Données** | Slugs internes / flags déjà gérés par le service (`verified_flag_slug`, `phone_verified_at`, etc. — voir events dans `service.py`). |
| **Validations** | Complétion interaction avant `next` ; déjà appliqué par `_ensure_interaction_advance_allowed`. |
| **Dépendances** | Numéro soumis à l’étape précédente (contexte session). |
| **Existe déjà** | Types d’écran `interaction` + `phone_verification_sms` ; endpoints `interaction/prepare|resend|complete`. |
| **Ajustements** | **Ajouter** un `registration_step_screen` (layout `interaction`) dans le flow EU en DB — soit nouveau step `phone_verification`, soit 2ᵉ screen du step `basic_info`. |

---

### Étape 3 — `residence`

| Aspect | Contenu |
|--------|---------|
| **Objectif** | LCB-FT / cohérence juridiction : pays de résidence, adresse, nationalité. |
| **Données** | `country_of_residence`, `city`, `address_line_1`, `postal_code`, `nationality` — **085**. |
| **Validations** | `policy_scope` residence + nationality ; listes pays (migrations politiques). |
| **Dépendances** | Aucune stricte ; logiquement après téléphone vérifié. |
| **Existe déjà** | Oui. |
| **Ajustements** | Option UX : remplacer progressivement champs texte par `address_step` / `address_autocomplete` (déjà supportés par Flutter) — **hors MVP minimal** si le seed texte suffit pour le premier jet. |

---

### Étape 4 — `professional`

| Aspect | Contenu |
|--------|---------|
| **Objectif** | Situation professionnelle et origine des fonds (AML basique). |
| **Données** | `employment_status`, `employer_name` (conditionnel), `annual_income_range`, `source_of_funds` — **085**. |
| **Validations** | Règles required + visibilité `employer` si `employed`. |
| **Dépendances** | Aucune. |
| **Existe déjà** | Oui. |
| **Ajustements** | Aucun obligatoire pour MVP. |

---

### Étape 5 — `risk_screening`

| Aspect | Contenu |
|--------|---------|
| **Objectif** | Profil investisseur réglementaire light (appropriateness). |
| **Données** | `investment_experience`, `known_asset_classes`, `risk_tolerance` — **085**. |
| **Validations** | Required sur les champs marqués required. |
| **Dépendances** | Aucune. |
| **Existe déjà** | Oui. |
| **Ajustements** | Aucun obligatoire. |

---

### Étape 6 — `consent`

| Aspect | Contenu |
|--------|---------|
| **Objectif** | Preuve de consentement contractuel et traitement des données. |
| **Données** | `terms_accepted`, `data_processing_consent`, `marketing_consent` — **085**. |
| **Validations** | Cases obligatoires cochées. |
| **Dépendances** | Dernier step avant `is_last_screen` + `complete`. |
| **Existe déjà** | Oui. |
| **Ajustements** | **Traçabilité** : pour un MVP sérieux, prévoir version de documents (champs ou `registration_execution_events`) — **Phase D ou compliance** (§9). |

---

## 4. OTP / phone verification strategy

### Quand vérifier le téléphone

**Recommandation MVP :** immédiatement **après** la saisie et validation **format + politique** du numéro à l’étape `basic_info`, **avant** les données d’adresse (résidence).

**Rationale :** sécuriser le canal SMS avant collecte sensible supplémentaire ; évite les abandons sur adresse si le numéro était incorrect.

### Intégration dans le flow

1. **Screen 1** (`basic_info_form`) : `submit` enregistre nom, email, téléphone, date de naissance → avance au **screen 2** du même step ou step suivant.
2. **Screen 2** (`interaction`, `phone_verification_sms`) :  
   - `prepare` / OTP / `complete` comme aujourd’hui dans `RegistrationPhoneSmsOtpPanel` ;  
   - puis `next` vers `residence`.

**Impact sur la progression**

- `progress_percent` : calculé côté serveur à partir de l’index d’écran dans le flow aplati — **ajouter un écran augmente le dénominateur** ; c’est cohérent (une unité de parcours de plus).
- `registration_session_steps` : le step `basic_info` peut rester `in_progress` jusqu’à la fin des deux écrans, ou être scindé — **préférence** : soit **un step** `basic_info` à **deux screens** (form + OTP), soit **deux steps** distincts pour clarté admin ; arbitrage §10.

### Ce qui existe déjà

- Blocage avancée si interaction incomplète (`StepBlockedError` / `_ensure_interaction_advance_allowed`).
- Panneau Flutter dédié.

---

## 5. Registration progress — modèle canonique (backend)

### Objectif

Une **seule** sémantique pour : runtime mobile, admin Customer 360, futures vues « dashboard client », sans recalculer des pourcentages divergents.

### Proposition de champs canoniques

| Champ | Type | Définition |
|-------|------|------------|
| `registration_stage` | `enum` (string stable) | Stade **macro** du lifecycle client, **dérivé** des sources ci-dessous. |
| `completion_ratio` | `float` 0..1 | Part du **pipeline global** retenu (inscription + KYC + PE + actif), **pas** seulement le formulaire. |
| `completed_steps` | `list[str]` | Identifiants de **jalons** (voir vocabulaire ci-dessous). |
| `missing_steps` | `list[str]` | Jalons manquants. |
| `registration_session_snapshot` | objet optionnel | `{ session_id, status, flow_version, progress_percent, current_step_key, current_screen_key, updated_at }` — **vérité runtime** pour l’état du formulaire. |

### Vocabulaire des jalons (aligné code existant)

Réutiliser les constantes déjà présentes dans `registration_progress.py` :

- `phone`, `identity_basics`, `registration_flow`, `kyc`, `pe_client_link`, `account_active`

**Évolution MVP :** distinguer explicitement dans les notes ou un sous-champ :

- **`registration_flow` complété** : dernière session registration avec `status == "completed"` **et** projection personne effectuée (déjà le cas quand `complete` a réussi).

### `registration_stage` — correspondance proposée

Réutiliser l’enum existante `RegistrationProgressStage` comme **canon admin** :

`phone_started` → `profile_partial` → `registration_active` → `registration_completed` → `kyc_pending` → `kyc_approved` → `pe_client_linked` → `active_client`

**Règle de priorité (du plus avancé au moins)** — alignée sur la logique actuelle de `compute_registration_progress` :

1. `active_client` si PE client actif  
2. sinon `pe_client_linked`  
3. sinon `kyc_approved`  
4. sinon `kyc_pending` si `kyc_status` ni `not_started` ni vide  
5. sinon `registration_completed` si session complétée  
6. sinon `registration_active` si session non complétée  
7. sinon `profile_partial` si nom/prénom en profil  
8. sinon `phone_started`

### Correspondance triple

| Source | Rôle |
|--------|------|
| **Runtime** `registration_sessions` | Détail **écran par écran** (`progress_percent`, `current_step_id`, `status`, `step_states`) — **vérité fine** du parcours. |
| **Admin** `compute_registration_progress` | Agrégat **lifecycle** ; à **faire converger** avec la définition ci-dessus (ajustements mineurs : ex. OTP vérifié pourrait influencer le jalon `phone` — §10). |
| **Future customer dashboard** | Même payload API que l’admin (ou sous-ensemble) : `registration_stage` + `registration_session_snapshot` + `completion_ratio`. |

### Event model (optionnel, déjà partiellement là)

- **`registration_execution_events`** : audit technique (déjà).
- **Évolution** : un événement métier unique `registration.lifecycle_changed` (hors scope implémentation immédiate) pour notifier changement de `registration_stage` — **Phase D** ou bus interne.

---

## 6. Completion strategy

### À la fin du parcours MVP (`POST .../complete`)

| Action | Comportement actuel (code) | Décision MVP |
|--------|----------------------------|--------------|
| **Projection** | `_project_to_person` → `profile_json["collected"]` (+ compliance slugs) | **Conserver** — reste le cœur. |
| **Person** | Création si besoin ; `kyc_status` initial `not_started` | **Option A (MVP minimal)** : laisser `not_started` puis job séparé → `kyc_pending`. **Option B (recommandée produit)** : passer à **`kyc_pending`** dans le même request de completion **après** projection pour signaler « prêt pour IDV ». |
| **pe_client** | Non créé dans `complete_session` | **Hors MVP obligatoire** ; **Phase C** : hook post-completion (queue ou appel service PE) si produit exige un compte portefeuille immédiat. |
| **Lien auth User ↔ Person** | Non dans registration service | **Post-auth** : à la création de compte ou login premier, attacher `person_id` (schéma existant à confirmer côté auth). |
| **Admin** | Customer 360 lit `registration_progress` | Après completion : stage **`registration_completed`** tant que KYC non démarré ; puis **`kyc_pending`** si Option B appliquée. |

### État final visible (cible)

- **Liste admin clients** : `registration_stage` = `registration_completed` ou `kyc_pending` selon option ; `completion_ratio` > seuil inscription seule.  
- **Détail client** : dernier `registration_session` en `completed` + aperçu des champs `profile_json.collected` (déjà partiellement couvert).

---

## 7. Data model decisions

### Mapping conceptuel

```
User (auth) ──optionnel──► Person ◄──registration_sessions.person_id
                              │
                              ├── profile_json (collected / compliance / computed)
                              ├── kyc_status
                              ├── client_id (nullable, lien PE si modèle existant)
                              └── pe_clients (0..1 typiquement)
```

### Source of truth vs dérivé

| Donnée | Source of truth | Dérivé |
|--------|-----------------|--------|
| Réponses brutes pendant le parcours | `registration_session_data` | — |
| Progression écran / step | `registration_sessions` + `registration_session_steps` | — |
| Profil post-inscription | `persons.profile_json`, `persons.kyc_status` | `registration_stage`, `completion_ratio` |
| Jalons lifecycle admin | Dérivés de Person + session + PE | — |

### Manques encore ouverts (sans inventer de colonnes)

- Table de **liaison explicite User ↔ Person** si absente du schéma auth — à confirmer hors registration.
- **Versioning des consentements** — pas de champ dédié dans le seed 085 ; à ajouter si compliance l’exige (événement ou champs dans `profile_json`).

---

## 8. Frontend implications

### Conserver

- `RegistrationFlowScreen`, `RegistrationFlowRenderer`, `RegistrationApi`, panneau OTP, hydration, validation téléphone locale.

### Modifier

- **`RegistrationTestLauncherScreen`** : renommer / intégrer dans un **vrai** point d’entrée onboarding EU (welcome ou post-login) — contenu produit, pas technique bloquant.
- **Écran de fin** : remplacer textes hardcodés par i18n ; message suivant le stage (`registration_completed` vs redirection KYC).

### Ajouter (phased)

- **Reprise** : persistance `session_id` (secure storage) + branchement `getCurrentScreen(sessionId)` ou `startSession` avec stratégie serveur (§9).
- **Indicateur de progression** : optionnellement stepper basé sur `step_states` / `progress_percent` déjà renvoyés.

### Reprise de session recommandée

1. Au `start`, si `session_id` local valide → `GET .../screen` ; si 404 / completed → nouveau `start`.  
2. Sinon `POST .../start` avec `jurisdiction=EU`.  
3. TTL / invalidation côté produit (ex. 7 jours) — arbitrage §10.

---

## 9. Backend implications

### Flows à ajuster

- **Flow EU actif** : insérer l’écran **interaction** SMS à l’emplacement défini en §4 (migration Alembic ou script admin selon process interne).
- Vérifier **885** : cohérence `is_last_screen` sur le dernier screen du step `consent`.

### Endpoints

- **Aucun nouveau endpoint obligatoire** pour le MVP si reprise = `GET screen` + `start` existants.
- **Optionnel** : `GET /api/registration/sessions/by-person/{person_id}` ou résolution via `person_id` sur `start` — **seulement si** le produit impose multi-devices sans partage de `session_id`.

### Validations à renforcer

- **Email** : format + unicité métier si requis (dépend modèle User — §10).
- **Cohérence** : même numéro E.164 entre step formulaire et interaction (déjà géré par contexte session).

### Post-completion hooks

- **Hook** (signal, tâche async, ou appel service) :  
  - mise à jour `kyc_status` → `kyc_pending` ;  
  - éventuelle création / liaison `pe_client` (Phase C).  
- Implémentation : **hors** grosse refonte — un point d’extension unique dans ou après `complete_session`.

---

## 10. Open questions (arbitrages réels)

1. **OTP dans le même step ou step dédié** — impact admin (`step_states`) et lisibilité métier.  
2. **Unicité email / téléphone** : règle globale (conflit compte existant) — implique auth.  
3. **Quand créer le lien User ↔ Person** : avant registration, après OTP, ou à la fin — impact fraude et support.  
4. **kyc_pending** : dans `complete` synchrone vs job async — latence et idempotence.  
5. **pe_client** : obligatoire dès fin registration ou seulement après KYC approuvé — impact Phase C.  
6. **Durée de vie session** abandon : politique exacte pour resume.  
7. **Consentements** : besoin de hash de version légal pour preuve — compliance.

---

## 11. Recommended implementation plan

### Phase A — Alignement flow + progress

- Ajuster le **flow EU** en DB (écran OTP).  
- Aligner **`compute_registration_progress`** avec la définition canonique §5 (noms de jalons, `registration_completed` vs `kyc_pending`).  
- Renforcer validation **email** si arbitrage tranché.

### Phase B — OTP + resume

- Valider le parcours OTP de bout en bout sur mobile.  
- Implémenter **reprise** `session_id` + règles d’invalidation.

### Phase C — Completion + pe_client

- Hook post-completion : `kyc_pending` + éventuelle création **pe_client** / liaison.  
- Tests d’intégration admin : stages visibles cohérents.

### Phase D — Polish / admin visibility

- i18n écran fin ; consentements versionnés si requis.  
- Dashboard client / détail champs collectés ; optional événements lifecycle.

---

## Arbitrages recommandés (synthèse)

| Sujet | Recommandation |
|-------|----------------|
| Moteur | **Registration engine uniquement** pour le parcours EU MVP |
| Onboarding engine | **Ne pas** l’utiliser pour cette collecte ; périmètre futur séparé |
| OTP | **Juste après** `basic_info` (écran dédié interaction) |
| Vérité progression formulaire | **`registration_sessions`** + payload runtime |
| Vérité lifecycle produit | **`registration_stage`** + jalons §5 dérivés de Person / session / PE |
| Completion | **Projection Person** + **`kyc_pending`** recommandé pour enchaîner IDV |
| pe_client | **Phase C**, pas bloquant au tout premier MVP si le produit accepte « Person seule » |

---

*Document prêt pour revue produit / compliance / tech avant implémentation.*
