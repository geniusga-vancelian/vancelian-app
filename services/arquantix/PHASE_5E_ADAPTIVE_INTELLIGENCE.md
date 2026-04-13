# Phase 5E — Intelligence adaptive (segmentation + seuils dynamiques)

## Portée

Extension **déterministe** du moteur Phase 5C/5D (`risk_engine.py`) et de la friction adaptive (`continuous_auth_engine.py`). **Pas de ML**, pas de second moteur, pas de réécriture d’architecture.

**Activation** : variable d’environnement `ADAPTIVE_INTELLIGENCE_ENABLED=true` (défaut : désactivé — comportement inchangé).

## Segmentation

Segments : `new_user`, `normal_user`, `trusted_user`, `high_value_user`, `risky_user`.

**Entrées** (`UserSegmentationInput`, optionnelles) :

- `account_age_days` (depuis `current_user.created_at` ou équivalent)
- `total_volume_eur` (en-tête `X-User-Lifetime-Volume-Eur`)
- `successful_actions_count` (`X-User-Successful-Actions-Count`)
- `historical_anomaly_count` (`X-User-Historical-Anomaly-Count` ou `intelligence.historical_anomaly_count`)
- `kyc_level` (`X-User-Kyc-Level` ou attributs utilisateur `kyc_tier` / `kyc_level`)
- `trust_level` (en-tête ou SI)

**Ordre de priorité** (`derive_user_segment`) :

1. `historical_anomaly_count >= 2` → `risky_user`
2. `account_age_days < 7` → `new_user`
3. `total_volume_eur >= 50_000` EUR → `high_value_user`
4. `account_age_days >= 90`, pas d’anomalies, KYC compatible (`VERIFIED` / `FULL` / `GOLD` / `ADVANCED` ou KYC absent) → `trusted_user`
5. Sinon → `normal_user`

## Ajustement de score

Facteur unique `user_segment_adjustment` (poids clampé comme les facteurs comportementaux) :

| Segment        | Poids |
|----------------|-------|
| trusted_user   | −10   |
| high_value_user| −5    |
| new_user       | +10   |
| risky_user     | +20   |
| normal_user    | 0     |

**Garde-fous** : les poids **négatifs** ne s’appliquent pas si le score « préliminaire » (sans ce facteur) est déjà **critique** au sens des seuils par défaut 50/75, si `require_reauth` est imposé par le contexte strict, ou si la vélocité géographique brute ≥ 40 (anomalie forte). Les ajustements **positifs** (new/risky) s’appliquent toujours.

## Seuils de niveau de risque (high / critical)

| Segment         | high | critical |
|-----------------|------|----------|
| trusted_user    | 60   | 80       |
| new_user        | 40   | 65       |
| risky_user      | 40   | 65       |
| high_value_user | 55   | 75       |
| normal_user     | valeurs passées à `evaluate_request_risk` (souvent `RISK_HIGH_THRESHOLD` / `RISK_CRITICAL_THRESHOLD`) |

## Friction adaptive (Phase 5B + 5E)

Lorsque `ADAPTIVE_INTELLIGENCE_ENABLED` est actif, les seuils utilisés par `_adaptive_friction_wallet_transfer` et `_adaptive_friction_view_sensitive` deviennent **par segment** :

| Segment         | Montant bas risque (EUR) | Fenêtre auth récente (s) | Tolérance appareil (obs.) |
|-----------------|---------------------------|---------------------------|----------------------------|
| new_user        | 100                       | 300                       | 0.9                        |
| normal_user     | 500                       | 900                       | 1.0                        |
| trusted_user    | 2000                      | 1200                      | 1.2                        |
| high_value_user | 5000                      | 900                       | 1.1                        |
| risky_user      | 50                        | 120                       | 0.65                       |

`device_tolerance` est exposé dans `dynamic_thresholds_used` pour observabilité ; le scoring appareil Phase 5D reste inchangé (pas de multiplication silencieuse des poids appareil dans cette phase).

## Décision recommandée (`recommended_outcome`)

- **trusted_user** + niveau **medium** → `allow` (moins de step-up si le reste du contexte le permet).
- **risky_user** + niveau **medium** → `step_up` (escalade systématique).
- Les cas **critical**, **reauth** strict, et **overrides** comportementaux (ex. vélocité géographique) restent prioritaires et ne sont **pas** contournés.

## Observabilité

- `RiskEvaluation.user_segment`
- `RiskEvaluation.dynamic_thresholds_used` (dict : montant EUR, secondes, `device_tolerance`)
- Journal `continuous_auth.risk_evaluated` : champs `user_segment`, `segment_adjustment`, `dynamic_thresholds_used`
- `ContinuousAuthDecision` : `user_segment`, `dynamic_thresholds_used` (via `_merge_risk_into_decision`)

## Limites

- Segmentation dépend de la **qualité des signaux** (en-têtes / SI / utilisateur) ; sans données, le segment retombe sur `normal_user`.
- Le reclassement `wallet_transfer` → `internal_transfer_low` (Phase 5C) continue d’utiliser les seuils **globaux** `LOW_RISK_*` depuis `security_env` (non segmentés dans cette itération).
- Aucun modèle statistique : tables et priorités sont **fixes** et auditables.

## Tests

`api/tests/test_phase5e_adaptive_intelligence.py` — segmentation, résolveurs, régression **5E désactivé**, scénarios **new / trusted / risky**.
