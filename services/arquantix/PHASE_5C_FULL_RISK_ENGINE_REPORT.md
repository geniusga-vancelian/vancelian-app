# Phase 5C — Rapport : moteur de risque dynamique (déterministe)

## Executive summary

Un **moteur de risque déterministe** (`risk_engine.py`) a été ajouté **au-dessus** de la pile existante (`sensitive_action_map`, `continuous_auth_engine`, friction adaptative Phase 5B). Il produit un **score 0–100**, un **niveau** (`low` / `medium` / `high` / `critical`), des **facteurs pondérés explicables**, et une **recommandation** (`allow` / `step_up` / `reauth`). Il **n’écrase jamais** une réauth stricte déjà requise ; il peut **augmenter** la friction (escalade) lorsque le score est élevé. Un chemin **documenté** de reclassement `wallet_transfer` → `internal_transfer_low` est appliqué uniquement lorsque toutes les conditions de sûreté (Phase 5B + score &lt; 25) sont remplies.

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `api/services/security/risk_engine.py` | Modèle de score, `evaluate_request_risk`, helpers, logs structurés |
| `api/tests/test_phase5c_risk_engine.py` | Tests unitaires et d’intégration Phase 5C |

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `api/services/security/security_env.py` | `RISK_ENGINE_ENABLED`, `RISK_HIGH_THRESHOLD`, `RISK_CRITICAL_THRESHOLD` |
| `api/services/security/continuous_auth_engine.py` | Champs risque sur `ContinuousAuthDecision`, appel au moteur après strict + adaptatif, fusion (escalade) |
| `api/services/security/session_intelligence_dependencies.py` | En-têtes `X-Transfer-Same-Owner`, `X-Recent-Similar-Actions`, passage du contexte, enrichissement `detail` |
| `api/services/security/continuous_auth_ux.py` | `risk_level` → tonalité UX ; priorités `risk_engine_*` |

## Modèle de scoring (3C)

### A. Score de base par action

| Action | Score |
|--------|------:|
| withdrawal | 55 |
| wallet_transfer | 45 |
| internal_transfer_low | 20 |
| beneficiary_add | 50 |
| api_key_create | 60 |
| security_settings_change | 50 |
| passcode_reset | 55 |
| biometric_disable | 45 |
| contact_change | 45 |
| view_sensitive_data | 30 |
| view_portfolio | 25 |
| data_export | 50 |
| session_revoke_all | 35 |
| change_password | 35 |
| *défaut* | 30 |

### B. Ajustements (somme algébrique)

| Facteur | Règle |
|---------|--------|
| Device | HIGH/TRUSTED : −15 ; MEDIUM : 0 ; LOW/UNKNOWN/manquant : +20 |
| Fraîcheur step-up | ≤ 5 min : −15 ; ≤ 15 min : −8 ; ≤ 60 min : 0 ; &gt; 60 min ou absent : +15 |
| Montant (retrait / transfert) | &lt; 100 : −10 ; 100–&lt;1000 : 0 ; 1k–&lt;10k : +10 ; 10k–&lt;50k : +20 ; ≥ 50k : +30 ; **montant absent** : +5 |
| Même titulaire | `true` : −10 ; `false` : +10 ; inconnu : 0 |
| SI session | `should_require_step_up` : +20 ; `should_force_reauth` : +35 ; `last_risk_score` ≥ 70 : +15 ; `country_changed` dans raisons : +35 |
| Rafale | 0–1 : 0 ; 2–4 : +10 ; 5+ : +20 ; **signal absent** : 0 (documenté) |
| Lecture sensible | view_sensitive_data : +10 ; data_export : +20 ; autres lectures simples : 0 |
| Signaux incomplets | `wallet_transfer` sans `same_owner` : +5 (montant déjà pénalisé séparément si absent) |

Score final = **clamp** somme des poids sur **[0, 100]**.

### C. Seuils de niveau (dérivés du score)

| Plage (par défaut) | Niveau |
|----------------------|--------|
| &lt; 25 | low |
| 25 à &lt; `RISK_HIGH_THRESHOLD` (50) | medium |
| 50 à &lt; `RISK_CRITICAL_THRESHOLD` (75) | high |
| ≥ 75 | critical |

Variables d’environnement : `RISK_HIGH_THRESHOLD` (défaut **50**), `RISK_CRITICAL_THRESHOLD` (défaut **75**).

## Recommandation (`recommended_outcome`)

1. Si le contexte strict indique **réauth requise** → `reauth` (le moteur ne downgrade pas).
2. Sinon, si niveau **critical** → `reauth`.
3. Sinon, si **high** → `step_up`.
4. Sinon, si **medium** → `step_up` **sauf** si friction adaptative Phase 5B a explicitement été appliquée (`adaptive_friction_applied`) → `allow`.
5. Sinon (**low**) → `allow`.

## Intégration dans `continuous_auth_engine`

Ordre : **1)** politique stricte **2)** friction adaptative (Phase 5B) **3)** si `RISK_ENGINE_ENABLED` et intelligence présente : `evaluate_request_risk` **4)** fusion :

- Réauth stricte : inchangée.
- Sinon, si recommandation `reauth` → `require_reauth=True`, `allow=False`.
- Sinon, si recommandation `step_up` et décision **autorisée** avant risque → escalade (`require_step_up`, biométrie réalignée sur la policy), codes `risk_engine_step_up` / `risk_engine_reauth`.
- **Aucune** remontée d’`allow` de `False` à `True` uniquement via le risque (pas d’affaiblissement hors chemins déjà prévus).

Champs additionnels sur `ContinuousAuthDecision` : `risk_score`, `risk_level`, `risk_factors`, `final_action_key`, `recommended_outcome`. `to_dict()` n’ajoute les clés risque que si renseignées (rétrocompatibilité).

## Downgrade `internal_transfer_low` (STEP 5)

Conditions **toutes** requises :

- `ADAPTIVE_FRICTION_ENABLED`
- `action_key == wallet_transfer`
- `amount_eur` présent et **&lt;** `LOW_RISK_TRANSFER_AMOUNT`
- `same_owner is True`
- `device_trust_level` ∈ {HIGH, TRUSTED}
- récence step-up ≤ `LOW_RISK_RECENT_AUTH_SECONDS`
- pas de `should_require_step_up` / `should_force_reauth` sur l’intelligence
- **score final &lt; 25**

→ `final_action_key = internal_transfer_low` + facteur `downgraded_to_internal_transfer_low` (poids 0, descriptif explicite). La policy globale dans `sensitive_action_map` n’est **pas** modifiée.

## Exemples documentés (STEP 12)

1. **Appareil fiable, auth récente, 50 EUR, même titulaire** — score bas, souvent `low` / `allow` ; downgrade possible vers `internal_transfer_low` si toutes les conditions.
2. **Fiable, récent, 1500 EUR wallet** — montant + base → souvent `medium` ou `high` → `step_up` (ou `reauth` si critique cumulée).
3. **Appareil inconnu, 200 EUR** — +20 device malgré petit montant → souvent ≥ `medium` → `step_up`.
4. **Inconnu, 25k retrait** — base + device + tranche montant → typiquement `critical` → `reauth`.
5. **Fiable, récent, lecture identité (`view_sensitive_data`)** — +10 périmètre lecture ; peut rester `medium` ; autorisé si friction adaptative Phase 5B a déjà levé le step-up **et** recommandation `allow`.
6. **`country_changed`** — +35 + souvent réauth côté strict ; le moteur aligne `reauth` si le contexte strict impose la réauth.

## Payload HTTP (`detail`)

Sur 401/403, lorsque le risque a été calculé : `risk_score`, `risk_level`, `risk_factors`, `recommended_outcome` ; `final_action_key` si différent de `action_key`.

## Observabilité

Logs (logger `arquantix.security.risk_engine`) :

- `continuous_auth.risk_evaluated` — métadonnées : clés d’action, score arrondi, niveau, codes de facteurs, présence montant, trust device, same_owner, recommandation (pas d’identité utilisateur brute).
- `continuous_auth.risk_downgrade_applied` — lors du reclassement `internal_transfer_low`.
- `continuous_auth.risk_escalation_applied` — lorsque la fusion impose step-up / réauth risque (via `continuous_auth_engine`).

## Tests ajoutés

Fichier `api/tests/test_phase5c_risk_engine.py` : bandes de niveau, device, montants, fraîcheur, same_owner, réauth stricte prioritaire, critique → reauth, intégration escalade, règles de downgrade, rétrocompat `to_dict`, logging, base score défaut.

## Limitations connues

- **Fréquence** : dépend de l’en-tête `X-Recent-Similar-Actions` ou d’un override programmatique ; sans signal, contribution 0.
- **Montants** : pas de devise autre que EUR dans le modèle actuel ; en-tête montant inchangé (Phase 5B).
- **Pas de ML** : scores entièrement explicables et reproductibles.
- **Clients anciens** : champs risque optionnels dans `detail` ; champs historiques inchangés.

## Pistes phase suivante

- Risque comportemental (vélocité géographique, patterns temporels).
- Profondeur empreinte appareil et corrélation multi-sessions.
- Cache compteur « actions similaires » côté serveur (Redis) pour remplacer l’en-tête volontaire.

## Configuration

| Variable | Défaut | Rôle |
|----------|--------|------|
| `RISK_ENGINE_ENABLED` | `false` | Active le moteur |
| `RISK_HIGH_THRESHOLD` | `50` | Borne inférieure du palier `high` |
| `RISK_CRITICAL_THRESHOLD` | `75` | Seuil `critical` |
| `ADAPTIVE_FRICTION_ENABLED` | `false` | Réutilisé pour downgrade + médium |
| `LOW_RISK_TRANSFER_AMOUNT` | `100` | Seuil montant petit risque |
| `LOW_RISK_RECENT_AUTH_SECONDS` | `900` | Fenêtre step-up pour reclassement |

## Synthèse « known risks »

- Mauvaise calibration des seuils → friction excessive ou insuffisante : ajuster `RISK_*` et poids en `risk_engine.py`.
- Omission d’en-têtes (`montant`, `same_owner`, rafale) → score plus conservateur (pénalités « absent » documentées).
