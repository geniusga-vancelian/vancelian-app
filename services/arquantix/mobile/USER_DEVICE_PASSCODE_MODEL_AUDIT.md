# USER_DEVICE_PASSCODE_MODEL_AUDIT.md

## Executive Summary

**Cause racine confirmée** du comportement « nouveau login → PasscodeSetup » : la déconnexion appelait explicitement `PasscodeService.clearPasscodeAndLockState()` dans `AuthLogout.signOut()`, ce qui **effaçait** le hash PIN, la biométrie et l’état de lockout **à chaque logout**. Le routage (`PostLoginLocalSecurityFlow`, `AppEntrySession`) lisait correctement `isPasscodeConfigured` ; la source de vérité était vide **par design du logout**, pas par bug de routing.

**Correctifs appliqués** :

1. **Logout** : ne supprime plus le passcode local (ni la préférence biométrique associée à ce binding).
2. **Stockage** : passcode (hash, sel, lockout, biométrie) **scopé par claim JWT `sub`** (`PasscodeUserKeys.forBinding`), avec **migration** des clés legacy globales vers le premier `sub` rencontré après mise à jour.
3. **Comportement multi-compte** : un autre `sub` sur le même appareil dispose de ses **propres** clés ; absence de PIN → `PasscodeSetup` comme attendu.

**Recommandation produit** : alignée sur une app fintech type **Option 3** (passcode **user + device**, persistant après logout pour **le même** utilisateur).

---

## Current Conceptual Model

### 1. « User » côté backend (confirmé partiellement)

- Le mobile ne modélise pas l’utilisateur serveur en base locale ; il consomme des **jetons** délivrés par l’API (FastAPI / auth). Les claims JWT sont lues côté client (`SessionService`, `SessionSecuritySnapshot`).
- **À vérifier côté API** : la valeur exacte de `sub` (e-mail, `person_id`, autre) selon le flux mobile — le client suppose une chaîne **stable par compte** pour la durée de vie des sessions.

### 2. « Session » côté backend / mobile

- **Session serveur** (vue mobile) : couple **access** + **refresh** stockés dans `FlutterSecureStorage` (`SessionStorageKeys`), avec refresh via `/auth/refresh` et révocation au logout (`revokeRemoteSession` puis `clearSession`).
- **Session locale** : étendue par des horodatages / claims persistés (`securityClaimsJson`, `lastLocalUnlockAtMs`, etc.) — **non effacés** par `clearSession()` (comportement observé dans le code : seuls access, refresh, expiry, greeting sont supprimés).

### 3. « Device » côté mobile

- Identifiants d’appareil / empreinte : `DeviceIdService` (hors périmètre détaillé ici). Le **passcode** est stocké dans le **Keychain / Keystore** de l’appareil, pas sur le serveur.

### 4. « Passcode » dans l’architecture (observé puis corrigé)

| Question | Réponse (après audit + correctifs) |
|----------|-------------------------------------|
| Local uniquement ? | **Oui** — jamais envoyé au backend. |
| Lié à un user ? | **Oui** — clés suffixées par un identifiant dérivé du **`sub` JWT** (quand le token est un JWT à 3 segments). |
| Lié à un device ? | **Oui** — stockage uniquement sur l’appareil. |
| Survivait au logout (avant) ? | **Non** — `AuthLogout` appelait `clearPasscodeAndLockState()`. |
| Survivant au logout (après) ? | **Oui**, pour le **même** `sub`. |
| Recréé à chaque login ? | **Non** pour le même compte ; **oui** si autre `sub` sans PIN enregistré. |

---

## Passcode Storage Audit

- **Service** : `PasscodeService` (`lib/features/security/passcode/data/passcode_service.dart`).
- **Support** : `FlutterSecureStorage`.
- **Clés** :
  - **Par utilisateur** : préfixe `arqx.sec.*.u.<suffix>` où `<suffix> = base64Url(utf8(sub))` sans `=` — voir `passcode_user_keys.dart`.
  - **Legacy** (sans `sub` exploitable) : clés historiques `arqx.sec.passcode_hash_b64`, etc. (un seul pool).
- **`isPasscodeConfigured()`** : après `init()`, lecture du hash pour le **binding courant** (JWT actuel) ; migration legacy → utilisateur si besoin.
- **Binding** : `SessionService.readAccessToken()` + `SessionService.extractJwtSubject(token)`.

---

## Logout Audit

**Fichier** : `lib/features/auth/application/auth_logout.dart`

| Action | Avant | Après |
|--------|--------|--------|
| `revokeRemoteSession` / `clearSession` | Oui | Oui |
| Efface access / refresh / expiry / greeting | Oui | Oui |
| `clearPasscodeAndLockState` | **Oui** | **Non** |

**Confirmé** : le bug venait **du logout**, pas du routing.

**Autres chemins** qui effacent encore le PIN : écran « Code d’accès oublié », lockout hard reset (`PasscodeVerifyHardReset`), effacement manuel des données app.

---

## Routing Audit

- **`AppEntrySession.resolveDestination()`** : `PasscodeService.init()` puis session valide puis `isPasscodeConfigured` — **cohérent** avec le binding JWT courant.
- **`PostLoginLocalSecurityFlow`** : après `storeTokens`, `init()` voit le nouveau token → **bon `sub`** → PIN existant → `SecureGate`.

Aucun changement de logique de routing nécessaire une fois le stockage et le logout alignés.

---

## User / Device / Passcode Relationship

- **Stratégie retenue** : **D + C** — passcode sur **device**, **isolé par `sub`** (compte). Pas de synchronisation serveur du PIN.
- **Cohérence** : adaptée au multi-compte sur un même téléphone (comptes distincts).

---

## Product Recommendation

- **Option retenue** : **Option 3** (passcode **user + device**, persistant après logout pour ce user).
- **Option 1** (global device, un PIN pour tous les comptes) : **rejetée** pour une app fintech.
- **Option 2** (PIN effacé à chaque login) : **rejetée** ; c’était l’effet involontaire du logout précédent.

**Style Revolut / néo-banque** : déconnexion **serveur** ≠ réinitialisation du **verrouillage appareil** pour le même profil ; autre profil → nouveau setup PIN si besoin.

---

## Fixes Applied

1. **`AuthLogout.signOut()`** : suppression de `PasscodeService.instance.clearPasscodeAndLockState()`.
2. **`PasscodeService`** : binding par `sub` JWT ; clés par utilisateur ; migration depuis les clés legacy ; `init()` recharge toujours le binding depuis le token courant.
3. **`SessionService.extractJwtSubject()`** : lecture du claim `sub`.
4. **`PasscodeUserKeys`** + **`passcodeBindingKeySuffix`** : construction des clés.

---

## Tests Added

- **`test/features/security/passcode/passcode_user_binding_test.dart`** :
  - `extractJwtSubject` (JWT valide vs opaque),
  - clés distinctes pour deux bindings,
  - clés legacy pour `binding == null`,
  - stabilité du suffixe.

**Non couvert en automatisé (à compléter si besoin)** : scénario E2E complet logout → login avec `flutter_secure_storage` réel ; comportement si **token opaque** sans `sub`.

---

## Final Verdict

- **Passcode** : **uniquement local** ; **non** stocké côté backend dans ce modèle.
- **Effacé au logout ?** : **Non** (après correctif), sauf actions explicites (oubli, hard reset sécurité).
- **Comportement cible** : même utilisateur (`sub`), même appareil → **Secure Gate** après login ; autre utilisateur → **PasscodeSetup** si aucun PIN pour ce `sub`.

---

## Remaining Open Questions

1. **Valeur de `sub` en production** (e-mail vs UUID) — à confirmer avec l’équipe API pour la doc sécurité.
2. **Token opaque** (non-JWT) : repli sur **clés legacy** partagées — **multi-utilisateur ambigu** ; à documenter ou à enrichir avec un autre binding (ex. hash stable du `person_id` fourni par l’API) si les tokens ne sont pas des JWT.
3. **`clearSession`** ne supprime pas `securityClaimsJson` ni certains horodatages — **hors scope** de ce correctif ; audit séparé si besoin de durcissement.
