# Registration EU — correctifs fin de parcours (T&Cs, passcode, session)

## Executive summary

Trois problèmes ont été traités sur le flux **signup mobile → OTP → passcode → registration EU → dashboard** :

1. **Double tap / impression que le dernier bouton ne réagit pas** — course async entre fermeture de modale et soumission, et premier tap parfois absorbé par le clavier ; correction par **await** du travail dans la modale téléphone et **unfocus** explicite avant le CTA final, avec un **handler unique** `_onLastScreenPrimaryTap`.
2. **Passcode redemandé juste après inscription** — redondance après double saisie du PIN ; **bootstrap** post-registration avec `forcePostAuthUnlock: false` et `skipPasscodeUnlock: true` (PIN déjà configuré et session valide ; pas de cold start).
3. **Dashboard « admin / test » au lieu du nouveau client** — le **BFF bootstrap** était appelé **sans** `Authorization: Bearer` ; en **404**, le client appelait **`select-default-client`**, ce qui liait le **client de test** admin. Désormais le **GET bootstrap** envoie le **Bearer** si présent, et **on ne déclenche plus** `select-default-client` lorsque l’utilisateur a déjà une session JWT.

---

## Cause racine — double clic / premier tap « mort »

- **Modale téléphone** : le bouton primaire utilisait un `Future.microtask` pour `_submitAndAdvance`, donc `await Modale.show` se terminait **avant** la fin réelle du submit ; l’enchaînement avec `_completeSession` pouvait être **hors ordre** ou donner l’impression qu’il « manquait » une action.
- **Correctif** : `ModaleButtonConfig.onTapAsync` exécute le submit **avant** fermeture de la feuille (`modale.dart`).
- **CTA dernier écran** : un **seul** handler `_onLastScreenPrimaryTap` enchaîne **submit (si champs input)** puis **`_completeSession`** ; **`FocusScope.of(context).unfocus()`** en tête pour limiter le cas où le premier tap ne fait que fermer le clavier.

---

## Cause racine — redemande du passcode

- **`forcePostAuthUnlock: true`** forçait un passage par l’écran de déverrouillage même juste après création du PIN.
- **`skipPasscodeUnlock: true`** (dans `AppEntryBootstrap`) n’est utilisé **que** lorsque le PIN est déjà configuré (le resolver sort avant sur welcome si pas de PIN). Cela évite la **3ᵉ** saisie sans affaiblir le cold start ni le flux login classique.

---

## Cause racine — mauvais utilisateur / client au dashboard

- **`HomeScreen._loadBootstrap`** faisait un **GET** non authentifié vers le BFF.
- En **404** (pas de client courant en dev), le client appelait **`POST .../bootstrap/select-default-client`**, ce qui sélectionnait le **client de test** — d’où l’alignement sur un compte « admin » attendu en local.
- Avec un **JWT** issu du signup, il faut que le bootstrap résolve le **bon** client côté BFF via **`Authorization: Bearer`**, et **ne pas** forcer le client test quand une session existe déjà.

---

## Correctifs appliqués

| Zone | Changement |
|------|------------|
| `mobile/lib/design_system/components/modale.dart` | `onTapAsync` sur le bouton primaire, await avant fermeture. |
| `mobile/lib/features/app_entry/application/app_entry_bootstrap.dart` | Paramètres `skipPasscodeUnlock` / `forcePostAuthUnlock` (déjà en place dans la branche). |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Modale téléphone : `onTapAsync` ; fin registration : `pushRootReplacingAll(..., forcePostAuthUnlock: false, skipPasscodeUnlock: true)` ; `_onLastScreenPrimaryTap`. |
| `mobile/lib/features/home/presentation/screens/home_screen.dart` | Bootstrap GET avec `Authorization: Bearer` si token ; pas de `select-default` sur 404 si Bearer présent. |

---

## Fichiers modifiés (récapitulatif)

- `mobile/lib/design_system/components/modale.dart`
- `mobile/lib/features/app_entry/application/app_entry_bootstrap.dart`
- `mobile/lib/features/registration/screens/registration_flow_screen.dart`
- `mobile/lib/features/home/presentation/screens/home_screen.dart`
- `REGISTRATION_FINAL_FLOW_BUGFIX_REPORT.md` (ce document)

**Backend** : aucun changement requis pour ce correctif ciblé ; si le bootstrap BFF renvoie encore **404** avec un Bearer valide, il faudra aligner le **route handler** Next/BFF pour résoudre le client à partir du JWT (hors périmètre du diff Flutter minimal).

---

## Flux utilisateur corrigé (attendu)

1. Dernier écran T&Cs / cases à cocher : **un tap** → submit serveur (si champs) → `completeSession` → navigation shell.
2. Pas d’écran passcode supplémentaire immédiatement après registration (PIN déjà posé).
3. Dashboard : bootstrap avec **session courante** ; plus de bascule automatique vers le client test admin lorsque l’utilisateur est authentifié.

---

## Tests / validations

### Vérifié en revue de code

- Enchaînement modale : `onTapAsync` → fermeture → pas de microtask orphelin.
- `AppEntryBootstrap` : `skipPasscodeUnlock` court-circuite uniquement après vérification PIN + session (voir ordre des gardes dans le resolver).
- Home : condition **404 + Bearer** → pas de POST `select-default`.

### Tests automatisés

- Non ajoutés (dépendance forte UI/modales/navigateur) ; possibles tests d’intégration sur `RegistrationApi` + mocks `SessionService` si la suite le permet.

### Manuel (recommandé)

1. Parcours complet EU jusqu’au dernier bouton : **un seul tap** suffit (avec et sans clavier ouvert sur un champ).
2. Après registration : **pas** de `PasscodeUnlockScreen` immédiat.
3. Dashboard : identité / devise / pastilles cohérentes avec le **nouveau** compte (pas le client test admin), avec API/BFF alignés sur le JWT.

---

## Limites restantes

- Si **`GET /api/mobile/flutter/bootstrap`** renvoie **404** même avec `Authorization: Bearer` (implémentation BFF incomplète), le client **ne** sélectionne plus le client test par défaut : les préférences bootstrap (devise, initiales) peuvent rester vides jusqu’à correction serveur.
- `skipPasscodeUnlock` ne doit **pas** être utilisé sur un cold start « session restaurée » sans garantie PIN — le code actuel ne l’emploie qu’à la **fin** du flux registration.
