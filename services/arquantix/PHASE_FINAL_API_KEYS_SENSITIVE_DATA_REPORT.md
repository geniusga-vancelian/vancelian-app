# Phase 4 — API Keys & exposition de données sensibles (rapport final)

## Executive Summary

Cette phase durcit les **lectures à fort impact** (identité consolidée KYC/AML, risque utilisateur, intelligence de session, journaux d’orchestration login) via **`require_continuous_auth_for_action("view_sensitive_data")`**, les hooks **`record_sensitive_action_completed` / `record_sensitive_action_failed`**, et le **détail structuré** déjà fourni par `session_intelligence_dependencies` (codes `session.reauth_required`, `session.step_up_required`, politique).

**Constat d’inventaire :** il n’existe pas, dans l’API FastAPI auditée, de routes dédiées **création / rotation / révocation de clés API « utilisateur »** (les occurrences `API_KEY` concernent des clés **fournisseurs** côté serveur). Aucun endpoint **export RGPD / CSV / PDF** dédié n’a été trouvé sous forme de route métier nommée ; la politique **`data_export`** reste dans `sensitive_action_map.py` pour branchement futur.

---

## Fichiers modifiés

| Fichier | Rôle |
|--------|------|
| `api/services/persons/routes.py` | `GET /api/persons/{person_id}/identity` |
| `api/services/portfolio_engine/clients/router.py` | `GET /api/portfolio-engine/clients/{client_id}/identity` |
| `api/services/auth/security_admin_routes.py` | Admin sécurité : risque utilisateur, preview orchestrateur, journaux, ligne session intelligence |

## Tests ajoutés

| Fichier | Contenu |
|---------|---------|
| `api/tests/test_phase4_sensitive_data_continuous_auth.py` | 401 / 403 sur identité personne avec mock `evaluate_request_security_context` ; succès sur `GET /admin/security/user-risk/{id}` avec décision `allow=True` |

---

## Inventaire (extrait — catégories demandées)

### A) Gestion de clés API (utilisateur)

| method | path | Router | Classification | Protect? | action_key | Raison |
|--------|------|--------|----------------|----------|------------|--------|
| — | — | — | — | Non | — | Aucune route « API key » utilisateur identifiée dans le périmètre FastAPI |

### B) Données sensibles — identité / KYC (implémenté)

| method | path | Router | Classification | Protect? | action_key | Raison |
|--------|------|--------|----------------|----------|------------|--------|
| GET | `/api/persons/{person_id}/identity` | persons | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Vue consolidée personne + client + éligibilité + risque |
| GET | `/api/portfolio-engine/clients/{client_id}/identity` | portfolio_engine.clients | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Même surface métier par `client_id` |

### C) Admin — risque / session / orchestration (implémenté)

| method | path | Router | Classification | Protect? | action_key | Raison |
|--------|------|--------|----------------|----------|------------|--------|
| GET | `/admin/security/user-risk/{user_id}` | auth.security_admin | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Profil risque et signaux pour un utilisateur |
| GET | `/admin/security/auth-orchestrator/preview` | auth.security_admin | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Simulation de stratégie de login pour un utilisateur |
| GET | `/admin/security/auth-orchestrator/decision-log` | auth.security_admin | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Liste d’événements `auth.login.orchestrated` (métadonnées `record_count`, `export_type`) |
| GET | `/admin/security/session-intelligence/logs` | auth.security_admin | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Événements `auth.session.*` (métadonnées `record_count`) |
| GET | `/admin/security/session-intelligence/{session_id}` | auth.security_admin | READ_ONLY_SENSITIVE | Oui | `view_sensitive_data` | Détail intelligence pour une session |

### D) Non protégés dans ce diff (justification)

| Exemple | Raison |
|---------|--------|
| `GET /admin/security/events`, `/events/summary`, `/anomalies` | Observabilité admin déjà restreinte par `get_current_user` ; périmètre volontairement minimal pour éviter régression. À réévaluer si politique « tout événement = sensible » est adoptée. |
| Routers portfolio_engine avec en-têtes `X-Actor-*` sans JWT | Le garde-fou `require_continuous_auth_for_action` s’appuie sur **`get_current_user`** (Bearer) ; les flux **ActorContext** seuls nécessiteraient une évolution d’architecture (hors scope Phase 4). |
| `GET /api/bundles` | Données catalogue marché, pas état financier utilisateur. |
| Health / public | Données non sensibles. |

---

## Classifications utilisées (STEP 2)

- **READ_ONLY_SENSITIVE** : endpoints couverts par `view_sensitive_data` dans ce livrable.
- **CREDENTIAL_MANAGEMENT** / **DATA_EXPORT** : mappés dans `sensitive_action_map.py` ; **aucune route** correspondante trouvée à ce jour pour `api_key_create` / `data_export`.

---

## Métadonnées hooks (STEP 4)

- **Identité** : `data_scope` (`kyc`), identifiants `person_id` / `client_id`, `sensitive_fields_accessed` lorsque pertinent.
- **Admin** : `data_scope` (`security_risk`, `auth_orchestration_preview`, `auth_security_events`, `session_intelligence`), `record_count` sur listes, `target_user_id` sur risque / preview.

---

## Ambiguïtés restantes

1. **Portfolio engine** : nombreuses routes exposent positions / historique avec modèle d’auth **headers acteur** ; traitement homogène avec l’auth continue JWT nécessite une décision produit (fusion des modèles ou second chemin de policy).
2. **Legacy** : `GET/POST /api/persons/{id}` et champs sans auth complet — déjà signalé en code (`TODO Phase 1C`) ; non retiré ici pour ne pas casser le contrat.
3. **`api_key_create` / `data_export`** : prêts en policy ; branchement lorsque des routes réelles existeront.

---

## Évaluation des risques

| Risque | Gravité | Commentaire |
|--------|---------|-------------|
| Lecture KYC sans step-up | Moyenne | `view_sensitive_data` est en **MEDIUM** avec `trusted_only` ; pas de step-up obligatoire par défaut sur la policy (aligné map existante). |
| Admin sans auth continue si `CONTINUOUS_AUTH_ENABLED=false` | Faible | Comportement historique inchangé. |
| `db.commit()` dans handlers après hooks | Très faible | Aligné passkeys / custody ; en tests transactionnels, avertissements SQLAlchemy possibles sans échec fonctionnel. |

---

## Recommandation — phase suivante

1. **Décider** du périmètre **portfolio_engine** (JWT + ownership vs ActorContext) avant d’étendre `view_sensitive_data` ou `view_portfolio`.
2. **Éteindre** l’accès legacy aux personnes lorsque la migration client est terminée.
3. **Brancher** `data_export` / `api_key_create` dès apparition d’endpoints réels.

---

## Readiness

- **Prêt pour merge** : oui, diff limité, tests verts sur les nouveaux cas et régression identité / SIEM admin.
- **Activation** : protection effective lorsque `CONTINUOUS_AUTH_ENABLED` et `SESSION_INTELLIGENCE_ENABLED` sont actifs **et** JWT avec `sid` (session liée), comme pour les phases précédentes.
