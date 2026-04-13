# Phase 5 — Risk Engine Product Dashboard

Ce document décrit les **endpoints** d’agrégation, les **métriques**, la **UI** admin Next.js, les **alertes**, et des **exemples** de réponses JSON.

## Portée et limites

- Les séries sont stockées **en mémoire dans le processus API** (`deque` bornés). En déploiement multi-instances, chaque worker ne voit que son trafic ; pour une vue globale, prévoir plus tard Redis / agrégation centralisée ou export vers un entrepôt.
- Les évaluations sont enregistrées à chaque retour du moteur de risque ; les feedbacks à chaque enregistrement de feedback (calibration / produit).

---

## Endpoints (backend FastAPI)

Base path : `/admin/security`

Tous les endpoints ci-dessous exigent un **utilisateur admin authentifié** (même mécanisme que le reste de l’admin).

| Méthode | Chemin | Query |
|--------|--------|--------|
| GET | `/risk-dashboard/summary` | `window_hours` (défaut `24`, plage `1`–`168`) |
| GET | `/risk-dashboard/factors` | `window_hours` |
| GET | `/risk-dashboard/segments` | `window_hours` |
| GET | `/risk-dashboard/experiments` | `window_hours` |
| GET | `/risk-dashboard/alerts` | `window_hours` |
| GET | `/risk-dashboard/recent` | `limit` (défaut `50`, max `200`) |
| GET | `/risk-dashboard/calibration-suggestions` | — |

Fichiers : `api/services/security/risk_dashboard_routes.py`, `api/services/security/risk_dashboard_store.py`.

---

## Définitions des métriques

### Résumé (`/summary`)

| Champ | Description |
|-------|-------------|
| `window_hours` | Fenêtre glissante en heures. |
| `sample_size` | Nombre d’évaluations dans la fenêtre. |
| `avg_risk_score` | Moyenne des scores de risque (0 si aucun événement : champs `null` côté agrégation vide). |
| `distribution` | Comptes par niveau : `low`, `medium`, `high`, `critical`. |
| `allow_rate` | Part des recommandations `allow` / `sample_size`. |
| `step_up_rate` | Part des `step_up`. |
| `reauth_rate` | Part des `reauth`. |
| `anomaly_detection_rate` | Part des évaluations avec au moins un signal comportemental (anomalie). |

### Facteurs (`/factors`)

| Champ | Description |
|-------|-------------|
| `top_factors_by_frequency` | Facteurs les plus présents sur les évaluations (fréquence). |
| `top_factors_in_fraud_feedback` | Facteurs associés aux feedbacks `fraud_confirmed` / `fraud_suspected`. |
| `top_factors_in_false_positive_feedback` | Facteurs pour `false_positive`. |
| `fraud_feedback_rate` | Part des feedbacks de type fraude parmi tous les feedbacks de la fenêtre. |
| `false_positive_rate` | Part des `false_positive`. |

### Segments (`/segments`)

Objet `by_segment` : pour chaque `user_segment`, `sample_size`, `avg_risk_score`, `allow_rate`, `step_up_rate`, `reauth_rate`.

### Expériences (`/experiments`)

Liste `variants` : lignes par couple `(experiment_id, variant)` avec taux d’outcomes, score moyen, et `critical_level_rate` (part de niveau `critical`).

**Friction delta (A/B)** : à dériver côté client en comparant `step_up_rate` + `reauth_rate` (ou `allow_rate`) entre variantes du même `experiment_id`.

### Alertes (`/alerts`)

Seuils configurables par variables d’environnement :

| Variable | Défaut | Condition |
|----------|--------|-----------|
| `RISK_DASHBOARD_ALERT_REAUTH_RATE_GT` | `0.35` | `reauth_rate` ≥ seuil si `sample_size` ≥ 20 |
| `RISK_DASHBOARD_ALERT_ANOMALY_RATE_GT` | `0.30` | `anomaly_detection_rate` ≥ seuil si `sample_size` ≥ 20 |
| `RISK_DASHBOARD_ALERT_FRAUD_FEEDBACK_RATE_GT` | `0.15` | `fraud_feedback_rate` ≥ seuil si `feedback_sample_size` ≥ 10 |

Réponse : `alerts[]` avec `id`, `severity`, `message` ; plus `thresholds` et `window_hours`.

### Décisions récentes (`/recent`)

Liste chronologique inverse : `ts`, `action_key`, scores, `recommended_outcome`, segment, variante d’expériement, `behavioral_anomaly`, `factor_codes`.

### Suggestions de calibration (`/calibration-suggestions`)

Réutilise `compute_calibration_suggestions` sur les snapshots de feedback du store ; retourne `suggestions` (schéma existant du module calibration) et `feedback_events_used`.

---

## Proxy Next.js

Les appels navigateur passent par :

`GET /api/admin/security/risk-dashboard/[[...path]]`

qui proxifie vers `${API_BASE_URL}/admin/security/risk-dashboard/...` avec le JWT admin (voir `web/src/app/api/admin/security/risk-dashboard/[[...path]]/route.ts`).

---

## UI admin (layout)

Page : **`/admin/security/risk-dashboard`**

- **Cartes KPI** : score moyen, taille d’échantillon, taux allow / step-up / reauth, taux d’anomalies.
- **Graphique** : distribution des niveaux de risque (barres).
- **Tableaux** : métriques par segment ; variantes d’expériences ; décisions récentes.
- **Alertes** : liste des alertes actives renvoyées par `/alerts`.
- **Calibration** : suggestions issues de `/calibration-suggestions`.

Entrée de navigation : **Admin → Risk dashboard** (icône bouclier) dans `AdminSidebar`.

---

## Exemples JSON (abrégés)

### `GET .../summary`

```json
{
  "window_hours": 24,
  "sample_size": 142,
  "avg_risk_score": 0.34,
  "distribution": { "low": 80, "medium": 40, "high": 18, "critical": 4 },
  "step_up_rate": 0.12,
  "reauth_rate": 0.05,
  "allow_rate": 0.83,
  "anomaly_detection_rate": 0.09
}
```

### `GET .../factors`

```json
{
  "window_hours": 24,
  "eval_sample_size": 142,
  "feedback_sample_size": 12,
  "top_factors_by_frequency": [
    { "factor_code": "device_new", "count": 45 }
  ],
  "top_factors_in_fraud_feedback": [["ip_risky", 3]],
  "top_factors_in_false_positive_feedback": [["velocity", 2]],
  "fraud_feedback_rate": 0.1667,
  "false_positive_rate": 0.0833
}
```

### `GET .../experiments`

```json
{
  "window_hours": 24,
  "variants": [
    {
      "experiment_id": "risk_ui_v1",
      "variant": "treatment",
      "sample_size": 60,
      "allow_rate": 0.78,
      "step_up_rate": 0.15,
      "reauth_rate": 0.07,
      "avg_risk_score": 0.38,
      "critical_level_rate": 0.03
    }
  ]
}
```

### `GET .../alerts`

```json
{
  "window_hours": 24,
  "alerts": [
    {
      "id": "spike_reauth",
      "severity": "warning",
      "message": "Taux de reauth élevé (38.0% ≥ 35%) sur la fenêtre."
    }
  ],
  "thresholds": {
    "reauth_rate": 0.35,
    "fraud_feedback_rate": 0.15,
    "anomaly_rate": 0.3
  }
}
```

---

## Fichiers touchés (référence)

| Zone | Fichiers |
|------|----------|
| Store + agrégations | `api/services/security/risk_dashboard_store.py` |
| Routes | `api/services/security/risk_dashboard_routes.py` |
| Enregistrement événements | `risk_engine.py`, `risk_feedback.py` |
| App | `api/main.py` |
| Proxy + page | `web/src/app/api/admin/security/risk-dashboard/...`, `web/src/app/admin/security/risk-dashboard/page.tsx` |
| Nav | `web/src/components/admin/AdminSidebar.tsx` |

---

## Métriques « produit » — correspondance

| Besoin produit | Où le trouver |
|----------------|----------------|
| % allow / step-up / reauth | `summary` (taux globaux) ; `segments` (par segment) ; `experiments` (par variante) |
| Taux fraude / faux positifs (feedback) | `factors.fraud_feedback_rate`, `factors.false_positive_rate` |
| Détection d’anomalies | `summary.anomaly_detection_rate` |
| Top facteurs (fréquence, fraude, FP) | `factors` |
| A/B conversion & friction | `experiments` (comparer variantes) |
| Drop-off après step-up | Non modélisé en natif dans ce MVP (nécessiterait un funnel événementiel dédié) |
