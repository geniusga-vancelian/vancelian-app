# Executive Summary

Ce durcissement **généralise** la politique déjà appliquée au bug « cold start + session valide + pas de PIN → ne pas rouvrir la création PIN » : une **grille unique** ([`PostAuthSensitiveFlowPolicy`](mobile/lib/features/app_entry/domain/post_auth_sensitive_flow_policy.dart)) documente les flux sensibles post-auth, et le **stockage session** nettoie désormais les **artefacts de sécurité volatiles** à la déconnexion et au **changement de compte** (`JWT sub` différent). Des **événements debug** ([`PostAuthFlowSecurityEvents`](mobile/lib/core/post_auth_flow_security_events.dart)) permettent un audit léger sans PII.

Les flux **normaux** (login → setup PIN ou Secure Gate **dans la même exécution**) restent inchangés. Les reprises **dangereuses après interruption** pour le setup PIN sont **neutralisées** (révocation session + welcome), comme avant ce chantier ; le rapport formalise et étend la couverture conceptuelle et technique.

---

# Sensitive Flows Inventory

| Flux | Point d’entrée | Prérequis | État local | État serveur | Risque si interrompu |
|------|----------------|-----------|------------|--------------|----------------------|
| **Setup passcode (1ʳᵉ fois)** | `PostLoginLocalSecurityFlow` → `AppNavRoutes.passcodeSetupBootstrap` | Jetons stockés, pas de PIN pour ce `sub` | Hash PIN (progressif jusqu’à succès) | Session API valide | Reprise cold start sur écran création PIN **sans** 2FA frais |
| **Déverrouillage local** | `PasscodeUnlockScreen`, `SecureGateScreen` | PIN configuré | Lockout, biométrie | JWT + claims sécurité | Faible si on **ré-entre** par l’écran prévu (pas un wizard partiel) |
| **OTP SMS / e-mail** | `LoginOtpScreen`, `LoginEmailOtpScreen`, etc. | Challenge actif | Controllers, timers | Challenge côté API | Reprendre un challenge **stale** après kill |
| **Passkey** | Orchestrateur login / passkeys | Credential request | État WebAuthn client | Session / challenge | Enrôlement ou assertion à moitié — **repartir du login** |
| **Forgot passcode** | `PasscodeUnlockScreen` → flux « oublié » | Selon impl. | — | — | Doit repartir d’une **entrée sûre** |
| **Secure Gate** | Cold start avec PIN OK | PIN + session valide | — | JWT | Passage normal par gate, pas reprise d’un sous-écran sensible |
| **Step-up / snapshot JWT** | `SessionSecuritySnapshot`, refresh | Claims dans secure storage | `securityClaimsJson`, horodatages | Step-up serveur | **Fuite d’état** entre utilisateurs si non nettoyé |

---

# Current Risks (avant / résiduel)

| Risque | Mitigation livrée |
|--------|-------------------|
| Session sans PIN au cold start | Inchangé et documenté : `AppEntryBootstrap` / `AppEntrySession` révoquent la session. |
| Artefacts session (claims, dernier unlock, compteurs bio) survivant au **logout** | `SessionService.clearSession()` supprime aussi les clés **volatiles** sécurité. |
| Changement de compte **sans** logout explicite (rare) : nouveau `storeTokens` avec autre `sub` | Détection **sub** différent → purge volatiles + événement `auth.post_auth_flow_invalidated_on_user_switch`. |
| Règles dispersées | Centralisation dans `PostAuthSensitiveFlowPolicy` + doc liée. |

**Résiduel** : les écrans OTP / passkey **isolés** ne passent pas tous par un mécanisme unique de « reset on resume » côté UI ; la politique est **déclarative** ; un durcissement UI supplémentaire (ex. invalider challenge au `AppLifecycleState.detached`) peut être ajouté par écran si besoin produit.

---

# Interrupted Flow Security Model

1. **Même exécution**, même session, même utilisateur (`sub`), flux enchaîné après login **sans** redémarrage app → **continuité autorisée** (ex. `PostLoginLocalSecurityFlow` → setup PIN → Secure Gate).

2. **Cold start / kill / crash / session incohérente** → **ne pas** reprendre un **wizard de sécurité** (setup PIN, OTP en cours, passkey enrollment) depuis un état **persisté** ambigu ; pour le PIN non terminé → **révocation session** + welcome (déjà en place).

3. **Changement d’utilisateur** → aucun état sécurité **session-level** (claims, unlock, compteurs) ne doit traverser le changement de `sub` ; PIN reste **par utilisateur** (clés `PasscodeUserKeys`).

Politique par type : voir `PostAuthSensitiveFlowPolicy.coldStartPolicy` et `PostAuthFlowTag`.

---

# Cold Start Hardening

- **Splash** → `AppEntryBootstrap.resolveInitialRootWidget` : session valide + **pas** de PIN → `revokeRemoteSession` + `WelcomeLandingScreen` + événement `auth.interrupted_sensitive_flow_revoked`.
- **`AppEntrySession.resolveDestination`** : même logique (tests / routeur) + même événement.
- **`SessionService.clearSession`** : suppression des clés volatiles (`securityClaimsJson`, `lastSensitiveActionAtMs`, `lastLocalUnlockAtMs`, compteurs biométrie).

---

# User Switch Isolation

- **`storeTokens`** : si un access token **existait** déjà et `sub` **≠** nouveau `sub`, purge des volatiles + événement (longueurs de `sub` uniquement, pas de PII).
- **PIN** : reste stocké par `sub` ; le compte A ne « mélange » pas le hash du compte B.

---

# Same-Execution Continuity Rules

- **Autorisé** : après `SessionService.storeTokens` réussi, navigation via `PostLoginLocalSecurityFlow.navigateReplacingLoginStack` vers setup PIN ou `AppEntryBootstrap.pushRootReplacingAll(forcePostAuthUnlock: true)`.
- **Refusé après cold start** : rouvrir **directement** `PasscodeSetupScreen` avec session déjà là sans nouveau login — évité par révocation (cf. bug corrigé).

Frontière : **runtime / même pile** vs **nouveau processus** (splash relance `resolveInitialRootWidget`).

---

# Events Added

| Événement | Déclencheur |
|-----------|-------------|
| `auth.interrupted_sensitive_flow_revoked` | Cold start / resolve destination sans PIN |
| `auth.post_auth_flow_invalidated_on_user_switch` | `storeTokens` avec changement de `sub` |
| `auth.post_auth_flow_resume_denied` | API réservée (hooks futurs) |
| `auth.post_auth_flow_resumed_same_execution` | Réservé (éviter spam) |

Émission : **debug uniquement** (`kDebugMode`), format `debugPrint` — brancher analytics plus tard si besoin.

---

# Tests Added

- `test/features/app_entry/post_auth_sensitive_flow_policy_test.dart` — politique pure.
- `app_entry_session_routing_test.dart` — `clearSession` nettoie volatiles ; `storeTokens` change de `sub` invalide unlock / JSON sécurité résiduel.

---

# Final Verdict

- **Reprises dangereuses** du type « session valide sans PIN → création PIN au cold start » : **déjà neutralisées** ; **documentées et instrumentées** (événements).
- **Flux sûrs** (login → setup PIN dans la même exécution) : **conservés** ; aucun changement de navigation post-login dans ce chantier.
- **Gaps résiduels** : challenges OTP / passkey **en cours** dans l’UI pourraient encore afficher un écran « stale » après kill selon timing ; mitigation recommandée = invalidation locale au `dispose` / lifecycle (hors périmètre minimal livré). La **politique centralisée** sert de référence pour les prochains PR ciblés.

---

# Remaining Gaps

1. Lifecycle par écran pour **invalider** challenge OTP / passkey au background prolongé (optionnel, produit).
2. Brancher `PostAuthFlowSecurityEvents` vers un **sink** analytics prod (sans `debugPrint`).
3. Aligner documentation **backend** (step-up, refresh) avec les mêmes termes si besoin transverse.
