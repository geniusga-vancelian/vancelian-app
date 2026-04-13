# Registration EU — fin de flow vers le dashboard (sans écran « success »)

## Point de départ

- Après `POST /api/registration/sessions/{id}/complete` réussi, `RegistrationFlowScreen` passait `_completed = true` et affichait un écran local **« Registration Complete »** avec un bouton **Done** (`Navigator.pop(true)`).
- L’utilisateur avait déjà une session JWT + passcode local ; l’écran success était redondant et retardait l’entrée dans l’app.

## Comportement cible

- Succès de `completeSession` → **même navigation** qu’après configuration du PIN hors parcours EU : `AppEntryBootstrap.pushRootReplacingAll(context, forcePostAuthUnlock: true)`.
- Résolution du shell : `MainShellScreen` ou `PasscodeUnlockScreen` selon `SecureAccessConfig` / `forcePostAuthUnlock`, **identique** au flux post-login documenté dans `app_entry_bootstrap.dart`.
- Échec réseau ou API : message d’erreur et `_submitting` remis à `false` — **inchangé**.

## Point de navigation retenu

- **`AppEntryBootstrap.pushRootReplacingAll`** (`mobile/lib/features/app_entry/application/app_entry_bootstrap.dart`) — aligné sur `PasscodeSetupScreen` (branche sans inscription EU en attente).

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Import `AppEntryBootstrap` ; suppression de `_completed`, de `_buildCompletedScreen`, et branche succès de `_completeSession` → `pushRootReplacingAll`. |

## Impact UX

- Fin d’inscription = **entrée directe** dans l’app (secure gate puis shell, ou shell selon config), sans page intermédiaire.
- Stack remplacée proprement (`pushAndRemoveUntil` … `false`) — pas de retour arrière vers le formulaire d’inscription depuis le shell.

## Tests automatisés

- Aucun test ajouté : les tests existants (`registration_launcher_test.dart`) ne couvrent pas le `complete` réseau ; le changement est purement navigation post-réponse API.

## Limites / cas particuliers

- **Test launcher** (`RegistrationTestLauncherScreen`) : ouverture du flow via `Navigator.push` + attente de `pop(true)` pour rafraîchir la liste. Avec **reset racine**, la route du flow est détruite **sans** `pop` — le `Future` du `push` peut se terminer avec une valeur autre que `true` ; l’utilisateur peut utiliser **Rafraîchir** sur l’écran test. Comportement debug acceptable.

## Confirmation non-régression

- **Backend** : non modifié ; toujours `completeSession` puis même session.
- **Login / session** : tokens inchangés ; seule la pile de navigation change.
- **Moteur registration** : `RegistrationApi.completeSession` inchangé.

## Raffinements futurs possibles

- Snackbar discret sur le shell après entrée (nécessiterait un mécanisme de message global ou `Navigator` + overlay).
- Rafraîchir automatiquement le test launcher via `RouteObserver` ou résultat de route — si le besoin debug augmente.
