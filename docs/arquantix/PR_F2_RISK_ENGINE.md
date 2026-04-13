# PR F.2 — Risk Engine intelligent (couche PR H)

## Rôle

Étend **PR F** sans le remplacer : pipeline **superposé** derrière des flags.

1. **Règles combinées** (non linéaires) — court-circuitent avec `block` ou `step_up`.
2. **Baseline utilisateur** — pénalité d’écart + mise à jour sur requêtes **autorisées**.
3. **Score pondéré** — alternative au score additif historique (`compute_risk_score`).
4. **Explicabilité** — `risk_reason` dans les réponses 403 et les logs.

## Flags

| Variable | Défaut | Effet |
|----------|--------|--------|
| `DEVICE_RISK_ENGINE_PR_F_ENABLED` | `false` | Maître PR F (inchangé). |
| `DEVICE_RISK_ENABLE_COMBINATION_RULES` | `false` | Active les règles combinées. |
| `DEVICE_RISK_ENABLE_BASELINE` | `false` | Active baseline + mise à jour `auth_user_risk_baselines`. |
| `DEVICE_RISK_USE_WEIGHTED_SCORE` | `false` | Utilise le score pondéré par dimension au lieu de l’additif. |
| `DEVICE_RISK_WEIGHT_*` | 0.3 / 0.2 / 0.3 / 0.2 | Poids device / réseau / comportement / historique. |
| `DEVICE_RISK_BASELINE_MIN_SAMPLES` | `5` | Observations mini avant pénalités baseline. |

## Règles combinées (ordre d’évaluation)

| Règle | Condition | Décision |
|-------|-------------|----------|
| `rule_new_device_and_country_change` | `profile is None` et pays ≠ dernier pays connu | **block** (score 100) |
| `rule_ip_change_and_attestation_low` | IP ≠ dernière IP et (trust LOW ou attestation absente/stale) | **block** |
| `rule_device_churn_and_velocity` | churn 24h ≥ 2 et vélocité > 0 | **block** |
| `rule_new_device_and_high_velocity` | profil absent et vélocité > 3 | **step_up** |

Implémentation : `services/auth/device_risk_engine_pr_f2.py` → `evaluate_combination_rules`.

## Baseline

Table **`auth_user_risk_baselines`** (migration **136**) :

- `countries_json` — compteur par code pays.
- `frequent_ips_json` — liste d’IP récentes (plafonnée).
- `device_count_ema`, `actions_per_hour_ema` — moyennes exponentielles.
- `baseline_sample_count` — nombre d’observations.

Pénalités (si `baseline_sample_count` ≥ seuil) : pays rare, IP inconnue, churn >> EMA.

Mise à jour : **`update_user_risk_baseline_from_observation`** — uniquement après décision **allow** (voir `require_low_risk_action`).

## Score pondéré

Les dimensions reprennent le découpage des points PR F, normalisées sur des plafonds internes puis :

`score = 100 × Σ(weight_i × min(1, raw_i / max_i)) / Σ(weights)`

## Réponses HTTP

Les détails 403 incluent **`risk_reason`** : liste de codes (`rule_*`, `dim_*`, `baseline_*`, signaux legacy).

## Exemple d’évaluation (logique)

**Contexte** : `DEVICE_RISK_ENGINE_PR_F_ENABLED=true`, `COMBINATION_RULES=true`, `BASELINE=true`, `WEIGHTED=true`.

1. Contexte construit (device, session, IP, pays, vélocité, churn, …).
2. Règle « IP + attestation faible » déclenchée → **block**, `risk_reason=["rule_ip_change_and_attestation_low"]` — fin.
3. Sinon baseline +0–40 selon écart.
4. Score pondéré + baseline → seuils `ALLOW` / `STEP_UP` / `BLOCK`.
5. Si **allow** : touch profil device + mise à jour baseline.

## Tests

- `tests/test_device_risk_engine_pr_f.py` — PR F additif inchangé.
- `tests/test_device_risk_engine_pr_f2.py` — F.2 (dont test baseline conditionnel si table migrée).

## Non-régression

- Tous les flags F.2 à `false` : pas de règles combinées, pas de bonus baseline, score = **additif historique** `compute_risk_score` (identique à PR F avant F.2).
- Les réponses incluent désormais **`risk_reason`** (signaux legacy / dimensions) pour l’audit — les seuils `allow` / `step_up` / `block` restent les mêmes si le score numérique est inchangé.
