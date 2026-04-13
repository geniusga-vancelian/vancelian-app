# Rapport — Identité Home / Profil / Mon compte (Flutter mobile)

## 1. Cause racine

### Symptômes observés

- Initiales génériques ou incohérentes dans la navbar Home (repli **JA** ou anciennes initiales).
- Page Profil peu fiable ; sous-titre « Mon compte » sans le bon e-mail.
- « Mon compte » : **Impossible de charger le profil** (`fetchProfile` → `null`).

### Causes identifiées (mobile)

1. **Plusieurs sources d’initiales sans règle unique**  
   - **Bootstrap** `GET /api/mobile/flutter/bootstrap` remplissait `ProfileLeadingPreference` via `client.initials`.  
   - **Profil** et **Mon compte** utilisaient `GET /api/mobile/flutter/profile` (BFF → `/api/app/profile`).  
   Les deux chemins sont cohérents côté backend une fois le JWT propagé, mais l’**ordre** et le **parallélisme** faisaient que la navbar pouvait rester sur le repli **JA** ou sur des initiales bootstrap **avant** que le profil canonique ne soit chargé — ou inversement sans garantie de **dernière écriture** par le même endpoint que Mon compte.

2. **Absence de couche unique après login**  
   Aucun chargement **systématique** du profil mobile (`fetchProfile`) au moment où la Home finit son bootstrap, alors que c’est **le même contrat** que la page Mon compte.

3. **Réponses HTTP non 200**  
   `MobileProfileApi.fetchProfile` retournait `null` sans log exploitable en debug — diagnostic difficile (401, 404 « No client profile linked to this session », 5xx, HTML).

4. **Garde async / changement de compte**  
   Les réponses profil pouvaient arriver après un **logout** ou un **switch** ; il manquait un **garde-fou** par **epoch** d’identité (`SessionIdentityContext.epoch`).

### Chaîne technique validée (BFF + API)

- **Flutter → Next** : `Authorization: Bearer` sur les routes `/api/mobile/flutter/*` (voir `upstreamHeadersWithAuth`).
- **Next → FastAPI** : `/api/app/bootstrap` et `/api/app/profile` avec le même header.
- **FastAPI** : `resolve_bootstrap_client` — avec Bearer, client **uniquement** depuis le JWT ; sans PeClient → **404**.

---

## 2. Cartographie des sources (avant / après correctif)

| Zone | Avant | Après |
|------|--------|--------|
| **Navbar Home** | `ProfileLeadingPreference` (bootstrap + fallback JA) | Même préférence, mais **rafraîchie** après chargement Home par **`ProfileIdentityCoordinator`** = même donnée que Mon compte |
| **Page Profil** | `MobileProfileApi.fetchProfile()` seul | **`ProfileIdentityCoordinator.refreshDisplayIdentity`** |
| **Mon compte** | `fetchProfile` direct | **Même coordinateur** (initiales + données identiques) |
| **Initiales** | Bootstrap JSON **et/ou** profil | **Canonique** : `GET …/profile` ; bootstrap ne fait plus « gagner » seul sur la durée sans passage par le coordinateur |

**Email / PII** : toujours issues de la projection `MobileAppProfile` (`GET …/profile`), alignée sur le **client résolu par JWT**.

---

## 3. Requêtes impliquées

| Requête | Rôle | Bearer |
|---------|------|--------|
| `GET /api/mobile/flutter/bootstrap` | `client.id`, devise, (initiales historiques bootstrap) | Injecté via `SessionBearerHttp` si jeton présent |
| `GET /api/mobile/flutter/profile` | Initiales + email + sections Mon compte | **Obligatoire** côté API profil (`SessionBearerPolicy.required` dans `MobileProfileApi`) |

---

## 4. Correctifs appliqués (code)

1. **`lib/core/profile_identity_coordinator.dart`**  
   - Appelle `MobileProfileApi.fetchProfile(accessToken: …)`.  
   - Met à jour `ProfileLeadingPreference` avec les initiales du profil.  
   - Ignore les réponses **obsolètes** si `SessionIdentityContext.epoch` a changé.

2. **`HomeScreen._loadAll`**  
   - Après `_loadBootstrap` + `Future.wait` des modules : si `hasSession`, **`await ProfileIdentityCoordinator.instance.refreshDisplayIdentity(debugTag: 'HomeScreen')`**.  
   - Garantit que la **navbar** reflète le **même** profil que Mon compte après le premier chargement.

3. **`ProfileScreen` / `AccountInfoScreen`**  
   - Utilisent le **même** coordinateur au lieu de dupliquer la logique `fetchProfile` + initiales.

4. **`MobileProfileApi`**  
   - Log debug `HTTP status` + longueur de corps quand `status != 200`.

---

## 5. Cache / état local

- **`ProfileLeadingPreference`** : reste le store UI des initiales ; réinitialisé au **logout** (`SessionService.clearSession` → `resetForLogout`).  
- **`SessionIdentityContext`** : `clear()` / `syncFromAccessToken` / `epoch` inchangés ; le coordinateur s’appuie sur **epoch** pour éviter d’appliquer un profil d’une session précédente.

---

## 6. Validations effectuées

- `flutter analyze` sur les fichiers modifiés (pas d’erreurs bloquantes sur le nouveau code).  
- Tests existants de session / bearer inchangés (à lancer : `flutter test test/core/session/`).

### Tests manuels recommandés

1. Login utilisateur A → Home : initiales A ; Profil : e-mail A ; Mon compte : données A.  
2. Logout → initiales replis / reset.  
3. Login utilisateur B → plus aucune donnée résiduelle de A.  
4. Kill app / relance avec session restaurée → même cohérence.

---

## 7. Risques restants

- **404** backend : *« No client profile linked to this session »* si le JWT est valide mais **aucun** `PeClient` lié (`person_id` / `sub`). Comportement attendu côté sécurité ; l’app affiche encore une erreur de chargement — à traiter produit (parcours onboarding / support).  
- **Environnement** : `API_BASE_URL` doit pointer vers le **BFF Next** (port 3000 en dev), pas directement sur FastAPI seul, pour les chemins `/api/mobile/flutter/*`.

---

## 8. Fichiers touchés (principaux)

- `mobile/lib/core/profile_identity_coordinator.dart` (nouveau)  
- `mobile/lib/features/home/presentation/screens/home_screen.dart`  
- `mobile/lib/features/profile/presentation/screens/profile_screen.dart`  
- `mobile/lib/features/profile/presentation/screens/account_info_screen.dart`  
- `mobile/lib/features/profile/data/mobile_profile_api.dart`  
