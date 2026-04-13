# Phase 5D.1 — Affinements comportementaux (baseline appareil, stabilité géo, rafales)

## Objectif

Raffiner le moteur Phase 5D (`api/services/security/risk_engine.py`) sans changer l’architecture : diff minimal, déterministe, facteurs toujours bornés (`clamp_behavioral_weight` : −20 … +40), score final toujours `[0, 100]`.

## Changements par facteur

### 1. Cohérence appareil (baseline vide vs nouveau vs connu)

| Cas | Code | Poids | Description |
|-----|------|-------|-------------|
| Empreinte présente, liste connue non vide, empreinte dans la liste | `device_known` | −10 | Appareil reconnu |
| Empreinte présente, liste non vide, empreinte absente | `device_new` | +20 | Nouvel appareil vs baseline |
| Empreinte présente, aucune baseline (`known_device_ids` vide) | `device_no_baseline` | +5 | Pas encore de référence (onboarding) |
| Empreinte absente + peu de signaux « nouveaux appareils » | `device_signal_absent` | 0 | Inchangé (early return) |
| Bonus historique « plusieurs nouveaux appareils » | (code inchangé côté logique) | +25 additif | Toujours cumulé puis clamp |

**Avant / après (exemple)** : utilisateur avec empreinte `fp1`, `known_device_ids=[]` → avant équivalent « nouveau device » +20 ; après **`device_no_baseline` +5** (moins de friction à l’onboarding).

**UX** : onboarding plus fluide. **Fraude** : la détection « vrai nouvel appareil vs liste existante » reste forte (+20).

### 2. Bonus stabilité géographique

- **Code** : `geo_stability_bonus`
- **Poids** : −5 (clampé comme les autres facteurs comportementaux)
- **Conditions** : `GEO_VELOCITY_ENABLED`, même pays courant / précédent, **pas** d’anomalie de vélocité (`raw_geo_velocity` issu de `_geo_velocity_factor` = 0), et au moins une des conditions :
  - dernière action &lt; 24 h, ou
  - SI : pas de `country_changed` dans `reason_codes_json` et `last_country` aligné sur le pays courant.

**Exclusion** : si `raw_geo_velocity > 0` (changement de pays / signal vélocité), **aucun** bonus — ne contredit pas `geo_velocity_anomaly`.

### 3. Rafales d’actions (homogène vs mixte)

Entrées optionnelles : `action_type`, `recent_action_types`, `same_type_action_count_5min` (contexte + en-têtes `X-Action-Type`, `X-Recent-Action-Types`, `X-Same-Type-Action-Count-5min`).

| Situation | Code | Poids (indicatif) |
|-----------|------|-------------------|
| `action_count_last_5min` ≤ 2 | `action_burst` | 0 |
| Données de type absentes (fallback Phase 5D) | `action_burst` | +10 si 3–5 actions, +25 si &gt; 5 |
| Types présents, même type ≥ 3 fois | `action_burst_homogeneous` | +20 (plafonné à +25 si n &gt; 5) |
| Types présents, rafale hétérogène | `action_burst_mixed` | +10 (idem plafond) |

**UX / fraude** : répétitions identiques = signal plus fort ; mélange d’actions = risque modéré.

## Observabilité

Les événements structurés existants (`continuous_auth.risk_evaluated`, `continuous_auth.behavioral_anomaly_detected`) incluent déjà `factor_codes` : les nouveaux codes **`device_no_baseline`**, **`geo_stability_bonus`**, **`action_burst_homogeneous`**, **`action_burst_mixed`** y apparaissent sans journaliser de données sensibles supplémentaires.

## Tests

Fichier : `api/tests/test_phase5d_behavioral_risk.py`

- Baseline appareil vide (`device_no_baseline` +5), appareil connu (`device_known`), nouveau vs liste (`device_new`).
- Stabilité géo (bonus −5, suppression si vélocité brute &gt; 0, absence de bonus si fenêtre récente + SI instables).
- Rafales : homogène / mixte / fallback sans types.
- Régression : scénarios Phase 5D (géo rapide → reauth, burst + gros montant → step-up, etc.), désactivation comportementale.

`tests/test_phase5c_risk_engine.py` : 24 tests OK (non régression Phase 5C).

## Compatibilité

- Pas de nouveau moteur ; API publique `evaluate_request_risk` inchangée.
- Clients sans les nouveaux en-têtes : comportement de rafale **identique** à l’ancien `action_burst` (fallback).
- Facteurs comportementaux toujours listés dans `RiskEvaluation.factors` avec codes explicites pour l’audit.
