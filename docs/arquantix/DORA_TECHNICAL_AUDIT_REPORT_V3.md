# Rapport d’audit technique V3 — Contrôles ICT, effectivité runtime et gouvernance (alignement DORA, lecture code)

**Service :** API Arquantix (`services/arquantix/api`)  
**Nature du document :** revue statique du code source et des migrations Alembic ; ce n’est pas une attestation de conformité DORA ni un avis juridique. Les sections 11–13 complètent le rapport par des **cadres de preuve** et des **limites explicites** : elles ne substituent pas des captures d’environnement de production ou un rapport de pentest réel.  
**Date de référence du dépôt :** généré à partir de l’état du code au moment de la rédaction.

---

## 1. Executive Summary

### 1.1 Périmètre exact

- Backend Python/FastAPI : `services/arquantix/api`.
- Migrations Alembic associées (notamment révisions 108+ sessions, 131+ refresh, 132–135 device/signature/attestation, 136–142 risque PR F.x).
- Hors périmètre : clients mobiles, frontaux web, infrastructure cloud (TLS, WAF, IAM), processus organisationnels non versionnés, registres de risques ICT hors dépôt.

### 1.2 Méthodologie

- Lecture ciblée des routeurs (`main.py`, `services/custody/router.py`), des dépendances FastAPI (`Depends`), de `services/security/security_env.py`, des modules `services/auth/device_risk_*.py`, `refresh_session.py`, `sensitive_action_events.py`, `session_intelligence_dependencies.py`, et du fichier `database.py`.
- Recherche globale des points d’ancrage du moteur PR F (`require_low_risk_action`).
- Aucun test d’intrusion, aucun audit d’exploitation, aucune validation des environnements de production.

### 1.3 Conclusion synthétique

Le dépôt contient une **architecture de contrôles en couches** (sessions rotatives, device, signatures ECDSA, attestation, moteur de risque PR F avec extensions F.2–F.7.2, auth continue, journalisation conditionnelle). En revanche, l’**application effective du moteur PR F unifié** (`evaluate_pr_f_for_request` via `require_low_risk_action`) est **limitée aux routes définies dans** `services/custody/router.py` — cinq points d’injection explicites. D’autres flux sensibles (login, refresh, passkeys, OTP, création bénéficiaire « simple-create ») s’appuient sur d’**autres** mécanismes ; en particulier, **`POST .../accounts/client/simple-create` n’inclut pas** `require_low_risk_action`, contrairement aux autres créations de compte client custody documentées dans le même fichier. Cette hétérogénéité est un point central pour un lecteur régulateur : **la conformité technique n’est pas homogène « route par route » pour une même famille métier.**

### 1.4 Limitations

- DORA n’est pas implémentée comme module logiciel ; le mapping ci-dessous est une **lecture ICT** des Articles et exigences usuelles, pas une certification.
- La conformité DORA complète suppose des preuves **organisationnelles** et **d’exploitation** hors seul code source.
- Les noms « PR A … PR G » sont une reconstruction logique ; il n’existe pas de fichier unique `pr_a.py` … `pr_g.py` couvrant l’historique.
- Les sections **11 à 13** exigent des **artefacts hors dépôt** (snapshot de configuration prod, journaux d’exploitation, procédure de changement signée, rapport d’intrusion ou de red team) pour être « opposables » seules : le dépôt fixe le **attendu logique** et les **variables d’environnement**, pas la valeur effective en production.

---

## 2. Scope and Methodology

### 2.1 Dépôts analysés

| Élément | Chemin |
|---------|--------|
| Application API | `services/arquantix/api/` |
| Migrations | `services/arquantix/api/alembic/versions/` |
| Présent document | `docs/arquantix/DORA_TECHNICAL_AUDIT_REPORT_V3.md` |

### 2.2 Fichiers et modules clés

| Domaine | Fichiers représentatifs |
|---------|-------------------------|
| Entrées HTTP auth | `main.py` (`/auth/login`, `/auth/refresh`, `/auth/revoke`, …) |
| Refresh / sessions | `services/auth/refresh_session.py` |
| PR F | `device_risk_engine_pr_f.py`, `device_risk_pr_f_dependencies.py`, `device_risk_engine_pr_f2.py`, `device_risk_engine_pr_f3.py`, `device_risk_dynamic_rules.py`, `device_risk_ml_engine.py`, `device_risk_temporal_engine.py`, `device_intent_engine.py` |
| Flux custody sensibles | `services/custody/router.py` |
| Signatures | `device_sensitive_signature.py`, `device_credentials_routes.py`, `device_pr_d3_policy.py`, `device_pr_d4_policy.py` |
| Attestation | `device_attestation_dependencies.py`, `device_attestation_service.py` |
| Auth continue | `services/security/session_intelligence_dependencies.py` |
| Feature flags | `services/security/security_env.py` |
| Modèles ORM | `database.py` |
| Journalisation actions sensibles | `services/security/sensitive_action_events.py` |

### 2.3 Hors périmètre

- Autres microservices ou monorepo hors `services/arquantix/api`.
- Configuration runtime (variables d’environnement réelles, secrets).
- Pentest, red team formalisé livrable : **NOT FOUND IN CODEBASE** comme livrable nommé ; des tests unitaires existent sous `tests/`.

---

## 3. Security Control Evolution by PR

| Réf. (logique produit) | Menace / objectif | Artefacts (code / DDL) |
|------------------------|-------------------|-------------------------|
| Sessions + rotation refresh | Rejeu de jeton refresh, gestion du cycle de vie | `AuthSession`, `AuthRefreshToken`, `AuthSpentRefreshJti` ; migration `131` ; `refresh_session.py` |
| PR D2 credentials | Lier requêtes à clé publique ECDSA | `auth_device_credentials` ; mig. `132` ; `device_credentials_routes.py` |
| PR D3 nonces | Anti-replay sur actions signées | `auth_device_signature_nonces` ; mig. `133` |
| PR D4 scope route | Nonce par route | colonne `route_path` ; mig. `134` |
| PR E attestation | Confiance matérielle / logicielle client | mig. `135`, `112` ; champs session ; `device_attestation_*` |
| PR F / F.2 / F.3 | Score risque, baseline | `device_risk_engine_pr_f*.py`, `auth_user_risk_baselines` |
| PR F.4 / F.4.1 | Règles dynamiques, validation DSL, dry-run | `auth_risk_rules`, `device_risk_dynamic_rules.py`, mig. `138`–`139` |
| PR F.5 | Administration règles | `risk_rules_admin_routes.py` |
| PR F.5.1 / F.5.2 | Simulation isolée | `risk_simulation_isolated.py` |
| PR F.6 | Intent / séquences | `auth_user_intent_events`, mig. `140`, `device_intent_engine.py` |
| PR F.7 / F.7.1 / F.7.2 | Pseudo-ML, gel EMA, temporel | `auth_user_risk_features`, `auth_user_temporal_features`, mig. `141`–`142` |
| Couche Redis (logique « PR G ») | Rate limit, cache, replay distribué | `redis_client.py`, `auth_redis.py`, `security_env.py` (`REDIS_ENABLED`, etc.) |

---

## 4. Security Architecture by Layer

| Couche | Rôle | Implémentation indicielle |
|--------|------|---------------------------|
| Identity | Résolution sujet JWT, lien `AdminUser` / `Person` | `jwt_subject_resolution.py`, `auth.py` |
| Session | Session serveur, refresh rotatif, révocation | `AuthSession`, `refresh_session.py` |
| Device | Profil par empreinte / `device_id` | `AuthUserDeviceProfile`, `normalize_device_id` |
| Signature | ECDSA P-256, nonces, scope route | `AuthDeviceCredential`, `AuthDeviceSignatureNonce`, modules PR D2–D4 |
| Attestation | En-têtes et politiques PR E | `require_device_attestation`, `device_attestation_service.py` |
| Risk (PR F) | Score agrégé, décision allow / step_up / block | `evaluate_pr_f_for_request` |
| ML (F.7) | Heuristique, z-score vs EMA | `device_risk_ml_engine.py` |
| Intent (F.6) | Séquences, anti-spam step_up | `device_intent_engine.py` |
| Temporal (F.7.2) | Distributions calendrier / transitions | `device_risk_temporal_engine.py` |
| Rules | Combinaisons F.2 + dynamiques F.4 | `device_risk_engine_pr_f2.py`, `device_risk_dynamic_rules.py` |
| Admin / ops | CRUD règles, simulation | `risk_rules_admin_routes.py`, `risk_simulation_isolated.py` |
| Redis | Cache identité, rate limit, nonces replay | Drapeaux dans `security_env.py` |

---

## 5. Sensitive Flow Coverage Matrix

Légende : **Oui** = présent sur la route dans le code ; **Non** = absent du handler ; **Cond.** = dépend d’un flag ou d’une configuration ; **N/A** = non applicable.

| Flux | Route(s) (observées) | JWT / session | Device binding | Signature requête (ECDSA) | Attestation | Risk PR F + ML + intent (si flags) | Rate limit / anti-replay | Piste d’audit | Risque résiduel |
|------|----------------------|---------------|----------------|----------------------------|-------------|--------------------------------------|---------------------------|---------------|-----------------|
| Login | `POST /auth/login` | Émission access + refresh ; session Phase 2 | `X-Device-ID` / attestation en headers | Non sur handler direct | Header `X-Device-Attestation` optionnel | **Non** (`require_low_risk_action` absent de `main.py`) | Middleware `AuthRateLimitMiddleware` sur l’app ; replay N/A pour login | Sessions `auth_sessions` ; logs module refresh | Compte compromis ; client faible |
| Refresh | `POST /auth/refresh` | Rotation ; alignement device | Oui (logique `perform_refresh`) | **Cond.** : `enforce_refresh_device_signature_if_configured` dans `refresh_session.py` | Header optionnel | **Non** PR F sur route | Spent JTI + chaîne refresh ; logs `refresh_token_*` | Tables `auth_refresh_tokens`, `auth_spent_refresh_jti` | Concurrence / config signature |
| Revoke | `POST /auth/revoke` | Corps refresh | Oui (`perform_revoke`) | Selon politique partagée avec refresh si applicable | Non explicite sur handler | **Non** PR F | Anti-replay refresh | Révocation session | Vol refresh valide avant révoquation |
| Revoke all | `POST /auth/revoke-all` | Bearer + `perform_revoke_all` | Vers Zero Trust | Non | Non | **Non** PR F | `enforce_zero_trust_or_raise` (hors mode test) | `record_sensitive_action_completed` → événements si `AUTH_SECURITY_EVENTS_ENABLED` | Dépendance ZT + flags |
| Add beneficiary (standard / canonical) | `POST /api/admin/custody/accounts/client`, `POST .../canonical` | `require_continuous_auth_for_action("beneficiary_add")` | PR F exige `X-Device-ID` si PR F activé | Non sur ces handlers | `require_device_attestation()` | **Oui** : `require_low_risk_action()` | Replay refresh N/A ; signature device sur autres routes | PR F : `device_risk_evaluated` ; intent si flag ; `record_sensitive_action_*` | — |
| Add beneficiary (simple EUR) | `POST .../accounts/client/simple-create` | `require_continuous_auth_for_action("beneficiary_add")` | Même espace headers | Non | `require_device_attestation()` | **Non** : pas de `Depends(require_low_risk_action)` | Idem | Idem partiel | **Écart de couverture** vs autres créations custody |
| Withdrawal (simu / replay webhook) | `POST .../simulate-withdrawal`, `POST .../webhook-events/{id}/replay` | Continuous `withdrawal` | Oui si PR F | Non | Oui | **Oui** PR F | N/A | `record_sensitive_action_*` | Simulation vs prod réelle hors périmètre code |
| Internal transfer | `POST /api/internal-transfer` | Continuous `wallet_transfer` | Oui si PR F | Non | Oui | **Oui** PR F | N/A | `record_sensitive_action_*` | En-têtes montant pour scoring contextuel |
| Security settings (agrégat) | Routes sous `security_admin_routes`, réglages session, etc. | `require_continuous_auth_for_action` selon route | Variable | Non dans extraits analysés | Non généralisé | **Non** PR F unifié sur ces handlers | Middleware global | Événements si activés | Couverture hétérogène |
| Passkeys | `POST /auth/passkeys/register/start|finish`, `POST .../revoke`, `GET ...` | Continuous (`security_settings_change` / `view_sensitive_data`) | Headers device dans flux | Non sur handlers lus | Non | **Non** PR F | Middleware global | `record_sensitive_action_*` | Pas de scoring PR F sur ces routes |
| OTP e-mail admin | Préfixe `/auth` (`admin_email_otp_routes.py`) | Flux OTP + `issue_fresh_auth_session` | Selon refresh | **NOT VERIFIED** exhaustivement dans cette passe | Références trust dans imports | **Non** PR F sur extrait | Limites module (TTL, tentatives) | `AuthAdminEmailOtpChallenge` | Enumération / interception canal |
| Local passcode ACK | `POST /auth/security/local-passcode-ack` | `get_current_user` | `X-Device-ID` optionnel (profil) | Non | Non | Non | N/A | Mise à jour `person.profile_json` | Renforce parcours produit, pas PR F |

**Preuve de couverture PR F :** la recherche `require_low_risk_action` dans `services/arquantix/api` ne retourne que `device_risk_pr_f_dependencies.py` et **`services/custody/router.py`** (cinq usages).

---

## 6. DORA-Oriented Control Mapping

DORA (UE 2022/2554) impose notamment une gestion intégrée des risques ICT, la détection et la gestion des incidents ICT, la résilience opérationnelle, et la documentation / contrôle fournisseurs. Le tableau ci-dessous **ne substitue pas** le texte légal ; il relie des **domaines ICT** à des éléments **observés dans le code**.

| Domaine d’exigence (ICT) | Contrôle technique observable | Composant / fichier | Preuve technique | Statut | Limite résiduelle |
|--------------------------|-------------------------------|---------------------|------------------|--------|-------------------|
| Identification et gestion des risques ICT | Feature flags, seuils, dry-run règles | `security_env.py`, `device_risk_dynamic_rules.py` | Drapeaux + journalisation dry-run | Partiel | Gouvernance des flags hors dépôt |
| Contrôle d’accès logique | JWT, sessions, rôles admin/ops, auth continue | `main.py`, `session_intelligence_dependencies.py`, `dependencies` custody | Code `Depends` | Partiel | Couverture inégale (§5) |
| Protection contre les incidents (détection) | PR F, intent, pseudo-ML, logs | Modules `device_risk_*`, `device_intent_engine.py` | Tables + logs `device_risk_*` | Partiel | Heuristiques, faux positifs |
| Résilience opérationnelle (service) | Redis optionnel, fallback | `identity_cache.py`, `security_env.py` | Configuration | Partiel | SPOF BDD, pas traité dans l’app |
| Traçabilité / preuve | Événements sécurité, intent, sessions | `AuthSecurityEvent`, `auth_user_intent_events`, `sensitive_action_events.py` | DDL + types d’événements | Partiel | `AUTH_SECURITY_EVENTS_ENABLED` désactive persistance |
| Cryptographie (usage) | ECDSA, nonces, WebAuthn côté serveur | Modèles D2–D4, `auth_passkeys` | Migrations 132+ | Partiel | TLS termination : **NOT FOUND IN CODEBASE** (infra) |

**Maturité par ligne :** voir section 10 ; globalement **Managed** à **Defined** selon domaine, rarement **Leading** au sens organisationnel complet.

---

## 7. Evidence Register

Pour chaque contrôle majeur : implémentation, persistance, logs, tests repérés.

| Contrôle | Code | Modèle / migration | Logs / événements | Tests (`services/arquantix/api/tests/`) | Commentaire |
|----------|------|--------------------|-------------------|----------------------------------------|---------------|
| Rotation refresh + reuse | `refresh_session.py` | `131`, `AuthRefreshToken`, `AuthSpentRefreshJti` | `refresh_token_reuse_detected`, `refresh_token_reuse_parallel`, etc. | `test_auth_refresh.py`, `test_auth_hardening_patch.py` | Preuve DB + logs |
| PR F évaluation | `device_risk_engine_pr_f.py`, `device_risk_pr_f_dependencies.py` | N/A | `device_risk_evaluated` | `test_device_risk_engine_pr_f.py` | Intent loggé post-éval si flag |
| Gel EMA ML (F.7.1) | `device_risk_ml_engine.py` | `141`, `AuthUserRiskFeatures` | Logs module ML | `test_device_risk_ml_engine.py` | Seuil `DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD` |
| Pseudo-ML F.7 | `device_risk_ml_engine.py` | `141` | idem | idem | Pas de lib ML externe dans le module |
| Temporel F.7.2 | `device_risk_temporal_engine.py` | `142`, `AuthUserTemporalFeatures` | `device_risk_temporal_evaluated`, `device_risk_temporal_ema_frozen` | `test_device_risk_temporal_engine.py` | — |
| Intent F.6 | `device_intent_engine.py` | `140`, `AuthUserIntentEvent` | Journal `auth_user_intent_events` | `test_device_intent_engine.py` | — |
| Règles dynamiques F.4 | `device_risk_dynamic_rules.py` | `138`–`139`, `AuthRiskRule` | `device_risk_rule_dry_run` (si dry-run) | `test_device_risk_dynamic_rules.py`, `test_device_risk_dynamic_rules_hardening.py` | — |
| Signature sensible PR D3/D4 | `device_sensitive_signature.py` | `132`–`134` | Échecs signature, rate limit | `test_device_pr_d4.py`, `test_device_pr_d3.py` | — |
| Attestation PR E | `device_attestation_dependencies.py` | `135`, champs `AuthSession` | Variables selon flux | `test_device_attestation_pr_e.py`, `test_device_attestation_tier1.py` | — |
| Auth performance PR C | `auth_performance_metrics.py`, `identity_cache.py` | N/A | Métriques internes | `test_auth_performance_pr_c.py` | — |
| Réputation device | `device_reputation_service.py` | migrations graphe | selon service | `test_device_reputation.py` | Hors matrice §5 si non sur route listée |

---

## 8. Threat Model and Defense Matrix

| Attaque | Contrôles observés | Statut | Résidu |
|---------|-------------------|--------|--------|
| Rejeu refresh après rotation | `AuthSpentRefreshJti`, chaîne `auth_refresh_tokens`, révocation | Mitigation forte | Fenêtre concurrentielle documentée dans le code |
| Usurpation d’IP/pays | En-têtes `X-Forwarded-For`, `CF-IPCountry` | Mitigation partielle | Confiance proxy/CDN |
| Contournement PR F sur route sans Depends | Absence de `require_low_risk_action` | **Gap** | Incohérence métier (ex. `simple-create`) |
| Replay signature sensible | Nonces + `route_path` + consommation DB | Mitigation (si activé) | Désactivation flags |
| Fraude lente / mimétisme | F.7, F.7.2, F.6 | Mitigation heuristique | Données insuffisantes, faux positifs |
| Abus credential device | Rate limit échecs signature | Mitigation partielle | Redis requis pour mode distribué |
| Compromission Redis | Clés non-JWT dans cache identité (doc module) | Mitigation conception | Exposition réseau Redis |

---

## 9. Residual Risks, Assumptions, and Dependencies

### 9.1 Flags désactivés

Si `DEVICE_RISK_ENGINE_PR_F_ENABLED` ou sous-flags (ML, temporal, intent, dynamic rules) sont à faux, les contrôles associés ne s’exécutent pas ou sont réduits. La preuve d’effectivité en production relève de la **configuration déployée** (hors dépôt).

### 9.2 En-têtes de confiance (proxy / CDN)

Les IP et pays utilisés dans le scoring et les profils proviennent des en-têtes HTTP. La fiabilité suppose une **terminaison TLS correcte** et une **configuration de confiance** des proxies en amont (**preuve infra hors code**).

### 9.3 Redis

Si `REDIS_ENABLED` est vrai : cache identité, rate limits distribués, replay nonces selon modules. Si faux : dégradations documentées dans les modules (comportement local ou désactivé selon cas).

### 9.4 PostgreSQL

Source de vérité pour sessions, règles, features, intent. Indisponibilité = indisponibilité des contrôles dépendants.

### 9.5 Attestation côté client

Le serveur ne peut valider que ce que le client envoie (`X-Device-Attestation`, etc.). La qualité de la preuve dépend du **runtime client** et des politiques OEM.

### 9.6 Limites heuristiques ML / temporal

Pas de modèle externe certifié ; scores explicables mais non calibrés par un organisme tiers dans ce dépôt.

### 9.7 Séparation code / organisation / preuves externes

| Type | Contenu |
|------|---------|
| Dans le code | Logique de contrôle, DDL, flags, tests unitaires |
| Gouvernance / processus | Revue des règles `auth_risk_rules`, gestion des incidents ICT, formation, gestion des changements |
| Hors dépôt | Configuration runtime, TLS, WAF, IAM cloud, contrats sous-traitants ICT, rapports de pentest |

---

## 10. Maturity Assessment and Recommended Next Steps

Échelle : **Initial** — **Managed** — **Defined** — **Advanced** — **Leading**.

| Domaine | Maturité | Forces | Gaps | Priorité remédiation | Action suivante |
|---------|----------|--------|------|----------------------|-----------------|
| Sessions et refresh | Advanced | Chaîne JTIs, spent table, tests auth refresh | Ops runbooks hors dépôt | Bas | Maintenir preuves déploiement |
| PR F (moteur) | Defined | Tests unitaires, couches F.2–F.7.2 | **Couverture route incomplète** | **Haute** | Harmoniser `Depends` (notamment `simple-create` vs autres) |
| Auth continue | Defined | Intégration session intelligence | Alignement avec PR F sur toutes routes sensibles | Haute | Matrice de couverture signée produit/sécurité |
| Signatures device | Defined | Nonces, scope route, tests D3/D4 | Non généralisé à tous flux financiers | Moyenne | Décider périmètre obligatoire signature |
| Pseudo-ML / temporal | Defined | Gel EMA, logs, tests | Calibration métier | Moyenne | Revue seuils et données d’entraînement implicites |
| Traçabilité SIEM | Managed | Hooks `sensitive_action`, PR F | Dépendance `AUTH_SECURITY_EVENTS_ENABLED` | Moyenne | Politique d’activation prod + rétention |
| Infra (TLS, Redis, PG) | NOT ASSESSABLE IN CODEBASE | N/A | Preuve d’architecture | Haute | Dossier infra pour due diligence |

---

## 11. Control Effectiveness and Runtime Evidence

Cette section répond à l’exigence d’**effectivité des contrôles** : distinction entre **capacité implémentée** (code) et **activation constatée** (runtime). La valeur **effective en production** n’est pas dans le dépôt ; les lignes « preuve requise » indiquent ce qu’un auditeur doit **collecter hors Git**.

### 11.1 Légende

| Statut effectif (à compléter par l’exploitant) | Signification |
|-----------------------------------------------|---------------|
| Attendu prod (recommandation) | Aligné sur une posture prudente pour un service financier ; non normatif juridiquement |
| Défaut code si variable absente | Valeur lorsque `os.getenv` retourne vide ou défaut documenté dans `security_env.py` / modules PR D2–D3 |

### 11.2 Registre d’effectivité (flags et preuves)

| Contrôle | Variable(s) / condition | Défaut si non défini (code) | Attendu prod (recommandation opérationnelle) | Preuve runtime requise (hors dépôt) | Si désactivé : risque résiduel |
|----------|---------------------------|-----------------------------|---------------------------------------------|-------------------------------------|-------------------------------|
| Moteur PR F | `DEVICE_RISK_ENGINE_PR_F_ENABLED` | `false` (`_env_truthy` défaut) | `true` pour routes où `require_low_risk_action` est monté | Export des variables d’environnement (hors secrets) ou config managée ; échantillon de logs `device_risk_evaluated` | Pas d’évaluation score / step_up / block PR F sur ces routes |
| Couche parente risque device | `DEVICE_RISK_ENABLED` | `false` | Cohérent avec PR F si utilisé | Idem | Selon usages de `is_device_risk_enabled()` dans le code |
| Règles dynamiques F.4 | `DEVICE_RISK_ENABLE_DYNAMIC_RULES` | `false` | `true` si politique de règles DB | Logs `device_risk_rule_*` / dry-run ; requêtes sur `auth_risk_rules` | Règles DB ignorées pour l’évaluation dynamique |
| Dry-run règles | `DEVICE_RISK_RULES_DRY_RUN` (+ override Redis `arquantix:risk:device_rules_dry_run` si Redis) | `false` | `false` en prod pour application effective | Capture Redis + env | Règles simulées seulement si dry-run à `true` |
| Combinaisons F.2 | `DEVICE_RISK_ENABLE_COMBINATION_RULES` | `false` | Selon politique | Logs / comportement | Sous-ensemble des règles statiques |
| Intent F.6 | `DEVICE_INTENT_ENGINE_ENABLED` (`is_device_intent_engine_enabled`) | `false` | `true` si détection de séquences requise | Lignes `auth_user_intent_events` + logs | Pas de journal intent ni motifs si `false` |
| ML F.7 | `DEVICE_RISK_ML_ENABLED` | `false` | `true` si couche heuristique requise | Logs ML ; table `auth_user_risk_features` | Pas d’overlay ML |
| Gel EMA ML (F.7.1) | `DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD` | `40` | Revue risque | Comportement persistance | Poisoning de baseline si seuil trop haut / mal calibré |
| Temporal F.7.2 | `DEVICE_RISK_TEMPORAL_ENABLED` | `false` | `true` si couche temporelle requise | `device_risk_temporal_evaluated` ; `auth_user_temporal_features` | Pas d’anomalies calendrier / transitions |
| Poids temporal | `DEVICE_RISK_TEMPORAL_WEIGHT` | `0.5` | Revue risque | Idem | Impact scoring réduit ou excessif |
| Cache risque PR F | `DEVICE_RISK_ENGINE_PR_F_CACHE_TTL_SEC` | `0` | Selon charge / risque | Métriques cache | Décisions non mises en cache si TTL 0 |
| Signature routes sensibles | `DEVICE_SECURITY_LEVEL` (`device_security_pr_d2.py`) | `0` | `>= 2` si signature + nonce requis sur politique documentée | Niveau effectif ; échecs `device_signature_invalid` | Niveau 0 : `sensitive_routes_device_signature_enabled()` faux (pas de signature obligatoire par ce critère) |
| Signature stricte refresh | `DEVICE_SIGNATURE_STRICT` | `false` | Selon menace | Logs refresh | Refresh possible sans signature selon branches |
| Redis (global) | `REDIS_ENABLED` | `false` | `true` si contrôles distribués requis | Santé Redis, métriques | Dégradation vers comportements locaux / désactivés |
| Replay nonce Redis | `DEVICE_NONCE_REPLAY_REDIS` (conditionné à Redis) | défaut activé si Redis | Idem | Métriques | Replay local vs distribué |
| Événements sécurité persistés | `AUTH_SECURITY_EVENTS_ENABLED` (cf. `is_security_events_enabled`) | Selon module | `true` pour traçabilité SIEM | Table `auth_security_events` ou sink | Pas de persistance d’événements si désactivé |

**Source des défauts :** `services/security/security_env.py`, `services/auth/device_security_pr_d2.py`, `services/auth/device_pr_d3_policy.py` (extraits audités).

### 11.3 Synthèse réglementaire (lecture ICT)

Les exigences DORA en matière de **mesures proportionnées** et de **surveillance** supposent que l’entité puisse **démontrer** que les mécanismes techniques pertinents sont **actifs** dans l’environnement cible. Le code prouve la **faisabilité** ; la **preuve d’activation** relève de la gouvernance d’exploitation (CI/CD, secrets manager, journaux centralisés). **NOT FOUND IN CODEBASE :** snapshot daté de configuration de production annexé à ce rapport.

---

## 12. Adversarial Validation (Red Team Findings)

### 12.1 Méthodologie et limite

Un rapport de red team **signé**, avec dates, périmètre et résultats d’exploitation, est **NOT FOUND IN CODEBASE**. La section ci-dessous formalise des **scénarios adverses**, le **comportement attendu** d’après la lecture du code, des **substituts de preuve** (tests automatisés), et une mention explicite lorsque le **résultat d’exécution réelle** n’est pas disponible dans le dépôt.

### 12.2 Scénarios

| Scénario | Défense attendue (logique code) | Substitut de preuve dans le dépôt | Résultat observé (prod / pentest) | Conclusion |
|----------|--------------------------------|-----------------------------------|-----------------------------------|------------|
| Vol de refresh token puis réutilisation après rotation | `AuthSpentRefreshJti` + révocation session ; erreurs HTTP 401 « Refresh token reuse detected » | `refresh_session.py` ; tests `test_auth_refresh.py`, `test_auth_hardening_patch.py` | **NOT AVAILABLE IN THIS REPOSITORY** | Risque résiduel : fenêtres concurrentielles documentées dans le code ; preuve opérationnelle à fournir |
| Usurpation d’identité « device » sans alignement JWT / session | `normalize_device_id`, contrôles session dans refresh | Tests device PR D2–D4 | **NOT AVAILABLE** | Résiduel : clients `legacy-unknown` ; chemins documentés dans `refresh_session.py` |
| Spoofing d’IP / pays (en-têtes) | Scoring PR F et profils utilisent `X-Forwarded-For`, `CF-IPCountry`, etc. | `device_risk_engine_pr_f.py`, `device_risk_pr_f_dependencies.py` | **NOT AVAILABLE** | Résiduel élevé si bordure non fiable — **preuve infra requise** |
| Fraude lente (comportement proche de la baseline) | F.7, F.7.2, F.6, F.3 | Tests `test_device_risk_ml_engine.py`, `test_device_risk_temporal_engine.py`, `test_device_intent_engine.py` | **NOT AVAILABLE** en conditions réelles | Résiduel : heuristiques ; faux négatifs possibles |
| Contournement de règle dynamique (DSL mal formé) | `validate_risk_rule_conditions` ; règle ignorée si invalide | `test_device_risk_dynamic_rules_hardening.py` | **NOT AVAILABLE** en prod | Résiduel : règle syntaxiquement valide mais sémantiquement dangereuse |
| Bypass PR F sur route métier | Absence de `Depends(require_low_risk_action)` | Matrice §5 (ex. `simple-create`) | **NOT AVAILABLE** | **Gap architectural** documenté : pas une attaque mais une incohérence de couverture |
| Manipulation Redis (effacement clés nonce / cache) | Dépend du déploiement réseau ; code ne prouge pas l’isolation réseau | `redis_nonce_guard.py`, `security_env.py` | **NOT AVAILABLE** | Résiduel : disponibilité et intégrité Redis ; ACL réseau hors scope code |

### 12.3 Exigence pour clôturer au niveau « institutionnel »

Pour équivaloir aux pratiques d’entreprises citées en référence par l’industrie (sans les nommer comme preuve de conformité du présent dépôt), il faut annexer :

1. Un **rapport de test d’intrusion** ou **red team** daté (ou campagne interne documentée).
2. Des **extraits de logs** ou tableaux de bord montrant les événements (`device_risk_evaluated`, `refresh_token_reuse_detected`, etc.) sur une période définie.
3. Un **registre de changement** pour les bascules de flags critiques.

---

## 13. Risk Governance and Change Management

### 13.1 Règles dynamiques (`auth_risk_rules`)

| Aspect | Implémentation observée dans le code | Piste d’audit | Risque humain | Atténuation technique |
|--------|----------------------------------------|---------------|----------------|------------------------|
| Création | `POST /admin/risk/rules` — `get_current_user` ; validation DSL via `validate_risk_rule_conditions` ; actions bornées `ALLOW` / `STEP_UP` / `BLOCK` | Ligne `AuthRiskRule` avec `created_at`, `version=1` | Erreur métier dans `conditions` si DSL valide mais ambigu | Validation DSL stricte ; échec HTTP 400 si invalide |
| Mise à jour | `PATCH /admin/risk/rules/{id}` — revalidation des `conditions` si fournies | `updated_at` en base | Changement non intentionnel | Même validateur |
| Activation | Champs `enabled`, `is_active`, `ruleset`, `priority` | Requêtes SQL / exports | Désactivation ou mauvaise priorité | Priorité numérique ; ruleset filtrable |
| Simulation | `POST /admin/risk/rules/simulate` ; mode `isolated` dans `risk_simulation_isolated.py` | Réponses `SimulateResponse` | Mauvaise interprétation des résultats | Champs `explain`, `dry_run_result` |
| Dry-run global | `DEVICE_RISK_RULES_DRY_RUN` ; override Redis documenté dans `security_env.py` | Logs dry-run | Règle jamais appliquée si dry-run oublié en prod | Revue de configuration (hors code) |

**Limite :** le code n’impose pas de **double validation** humaine (four-eyes) ni de **workflow de ticket** : **NOT FOUND IN CODEBASE** pour un moteur d’approbation obligatoire avant activation. La gouvernance procédurale doit être **externe** (processus interne, IAM admin).

### 13.2 Autres paramètres de risque

Les seuils PR F (`DEVICE_RISK_ALLOW_THRESHOLD`, `DEVICE_RISK_BLOCK_THRESHOLD`, etc.) sont des **variables d’environnement** : toute modification suit la **gouvernance du pipeline de déploiement** (hors dépôt). Aucun journal d’audit **humain** dédié aux seuls changements d’env n’apparaît dans le dépôt applicatif.

### 13.3 Synthèse

| Élément | Couvert par le code | Couvert par processus (à documenter hors dépôt) |
|---------|---------------------|-----------------------------------------------|
| Validation syntaxique des règles | Oui (`validate_risk_rule_conditions`) | Revue métier des règles actives |
| Traçabilité persistante des règles | Oui (table + horodatages) | Approbation et rôles IAM sur `/admin/risk/*` |
| Preuve de changement d’environnement prod | Non | Tickets, CAB, historique infra-as-code |

---

## Document control

- **Version :** V3 (sections 11–13 : effectivité runtime, cadre adversarial honnête, gouvernance des règles et limites).
- **Prochaine étape recommandée :** annexer snapshot de configuration prod (non secrets), extraits de logs, procédure de changement des règles, et rapport de pentest ou red team pour clôturer les « NOT AVAILABLE » de la section 12.
- **Fichier V2 :** `DORA_TECHNICAL_AUDIT_REPORT_V2.md` redirige vers ce document (V3).
