# Phase 5D — Rapport : risque comportemental & anti-fraude (déterministe)

## Executive summary

La couche **Phase 5D** étend `risk_engine.py` (sans second moteur) avec des **signaux comportementaux** explicables : géo-vélocité, risque pays, cohérence appareil, rafales d’actions, multi-sessions, ancienneté compte, méthode de connexion. Chaque facteur comportemental est **borné** individuellement **[−20, +40]** avant sommation dans le score global (clamp final **[0, 100]**). Des **règles dures** peuvent forcer **réauth** ou **step-up** sans ML. L’extraction des signaux se fait via **`extract_behavioral_context`** (en-têtes + session + intelligence + utilisateur), avec **dégradation gracieuse** si les données manquent.

## Fichiers modifiés / créés

| Fichier | Rôle |
|---------|------|
| `api/services/security/risk_engine.py` | Contexte `BehavioralRiskContext`, facteurs 5D, overrides, logs `continuous_auth.behavioral_anomaly_detected`, extension `RiskEvaluation` |
| `api/services/security/security_env.py` | `BEHAVIORAL_RISK_ENABLED`, `GEO_VELOCITY_ENABLED`, `DEVICE_RISK_ENABLED` |
| `api/services/security/continuous_auth_engine.py` | Paramètre `behavioral_context`, repli `extract_behavioral_context` si absent, passage `session` + contexte à `evaluate_request_risk`, codes `behavioral_force_*` |
| `api/services/security/session_intelligence_dependencies.py` | Construction du contexte via `extract_behavioral_context` si `BEHAVIORAL_RISK_ENABLED` |
| `api/services/security/continuous_auth_ux.py` | Priorité UX pour `behavioral_force_reauth` / `behavioral_force_step_up` |
| `api/tests/test_phase5d_behavioral_risk.py` | Tests unitaires & intégration |

## Liste des facteurs (codes)

| Code | Description courte |
|------|----------------------|
| `geo_velocity_anomaly` | Changement de pays vs délai (même pays = 0) |
| `geo_country_risk` | Niveau de risque du pays actuel (carte statique interne) |
| `device_consistency` | Appareil connu (−10), nouveau vs liste (+20), ≥3 nouveaux récents (+25) — combiné puis clampé |
| `action_burst` | Compteur d’actions sur 5 min (0–2 : 0 ; 3–5 : +10 ; >5 : +25) |
| `multi_session_risk` | Sessions actives (1 : 0 ; 2–3 : +5 ; >3 : +15) |
| `account_age_risk` | <1 j : +30 ; <7 j : +20 ; <30 j : +10 ; sinon 0 |
| `login_method_risk` | passkey : −10 ; OTP : 0 ; mot de passe seul : +10 |

Les facteurs **Phase 5C** (base, device trust SI, montants, etc.) restent inchangés et s’additionnent **avant** clamp global.

## Poids & intégration score

- **Somme** : `final_score = clamp_0_100(Σ poids)` incluant statique + comportemental.
- **Borne par facteur comportemental** : `clamp_behavioral_weight` ∈ **[−20, +40]** (appliqué à chaque contribution comportementale avant somme).

## Règles d’override (dures)

| Règle | Effet |
|-------|--------|
| Géo-vélocité **brute** ≥ **40** (ex. changement de pays &lt; 30 min) | `recommended_outcome = reauth`, `override_reason = behavioral_force_reauth` |
| **Nouvel appareil** (empreinte ∉ liste connue, liste non vide) **et** montant **> 10 000 EUR** sur `withdrawal` / `wallet_transfer` | `reauth` |
| **action_count_last_5min > 5** **et** action « haute valeur » (montant ≥ 1000 EUR sur transfert/retrait, ou montant absent sur retrait) | `step_up`, `behavioral_force_step_up` |

La **réauth stricte** issue de la policy / SI reste prioritaire dans la fusion `continuous_auth_engine`.

## En-têtes & signaux (extraction)

| En-tête / source | Usage |
|-------------------|--------|
| `X-Geo-Country`, `CF-IPCountry` | Pays courant |
| `X-Previous-Geo-Country` | Sinon `last_country` (SI) |
| `X-Last-Action-At` | Sinon `last_sensitive_action_at` / `last_activity_at` |
| `X-Device-Fingerprint` | Sinon `session.fingerprint_hash` |
| `X-Known-Device-Ids` | Liste d’empreintes connues (séparateurs `,` ou `;`) |
| `X-Session-Count-Recent` | Multiplicité sessions |
| `X-Action-Count-Last-5min`, `X-Action-Count-Last-1h` | Rafales (5 min utilisé pour `action_burst`) |
| `X-New-Devices-Recent-Count` | Complément cohérence appareil |
| `X-Login-Method` | Sinon `auth_strength` (SI / session) |
| `current_user.created_at` | Ancienneté compte |

**IP** : `request.client.host` (pas journalisée en clair dans les métadonnées d’anomalie au-delà du besoin — voir logs).

## Configuration

| Variable | Défaut | Rôle |
|----------|--------|------|
| `BEHAVIORAL_RISK_ENABLED` | `false` | Active toute la couche comportementale (hors géo/device si sous-flags off) |
| `GEO_VELOCITY_ENABLED` | `false` | Géo-vélocité + risque pays |
| `DEVICE_RISK_ENABLED` | `false` | Cohérence empreinte / appareils |

`RISK_ENGINE_ENABLED` doit rester à `true` pour exécuter le moteur.

## Observabilité

- `continuous_auth.risk_evaluated` — enrichi avec `behavioral_flags`, `override_reason`.
- `continuous_auth.behavioral_anomaly_detected` — lorsque des facteurs comportementaux sont présents ou des flags d’override ; métadonnées : `geo_change`, `device_new`, `action_burst`, `account_age_bucket`, `risk_score`, `flags`, `override` (pas d’identité ni montants bruts).

## Exemples (documentation)

1. **Dubai → Paris en 20 min** : changement de pays &lt; 30 min → poids brut 40 → **réauth** forcée.
2. **Nouvel appareil + retrait 20 kEUR** : override **réauth** si liste connue + empreinte absente de la liste.
3. **Appareil connu + petit transfert** : facteurs négatifs / score bas → **allow** si le reste de la pile l’autorise.
4. **Compte neuf + multiples transferts** : `account_age_risk` + `action_burst` → score élevé → souvent **step_up** ou blocage selon seuils.

## Limitations

- Pas de géolocalisation IP serveur : pays **fourni** par en-têtes / CF ou SI.
- Compteurs de rafale / sessions : **volontaires** via en-têtes tant qu’aucun agrégateur serveur n’est branché.
- Carte pays **statique** et simplifiée ; à affiner par conformité produit.

## Plan de rollout

1. Staging : `RISK_ENGINE_ENABLED=true`, `BEHAVIORAL_RISK_ENABLED=true`, `GEO_VELOCITY_ENABLED` / `DEVICE_RISK_ENABLED` par étapes.
2. Surveiller logs `behavioral_anomaly_detected` et taux de `behavioral_force_*`.
3. Production : activer d’abord **DEVICE** puis **GEO** selon qualité des signaux clients.

## Tests

`api/tests/test_phase5d_behavioral_risk.py` : géo, device, rafales, compte neuf, overrides, rétrocompat sans `BEHAVIORAL_RISK_ENABLED`, extraction, intégration `evaluate_request_security_context`.
