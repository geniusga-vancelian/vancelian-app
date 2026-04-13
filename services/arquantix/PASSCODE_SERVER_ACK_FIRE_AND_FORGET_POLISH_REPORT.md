# Passcode — ACK serveur en fire-and-forget (polish UX)

## Point de départ

- Après succès du double PIN, `PasscodeSetupScreen` enchaînait : `setPasscode` → `setBiometricUnlockEnabled(false)` → **lecture du token** → **`await ackLocalPasscodeRegistered`** → navigation (`pop` / registration / secure gate).
- L’`await` sur l’ACK liait la navigation au temps réseau (jusqu’à 3 tentatives + backoff + timeouts dans `SessionApi`), ce qui retardait inutilement l’UI alors que le PIN est déjà valide localement.

## Pourquoi le `await` a été retiré

- La **vérité locale** du passcode est établie dès que `PasscodeService.setPasscode` réussit ; l’ACK ne fait que refléter côté serveur un état déjà acquis sur l’appareil.
- Retarder la navigation pour un appel **idempotent** et **non bloquant métier** n’apporte pas de valeur UX ; l’objectif est une transition **immédiate** après succès PIN.

## Stratégie retenue

- **Ordre inchangé** : `setPasscode` et `setBiometricUnlockEnabled` restent **awaités** (cohérence locale garantie avant toute navigation).
- **Token** : toujours lu **avant** la navigation pour capturer le jeton courant (pas de course avec un logout synchrone improbable sur le même frame).
- **ACK** : lancé via `unawaited(SessionApi().ackLocalPasscodeRegistered(...))` **sans** attendre la fin.
- **Robustesse** : `.catchError((_, __) {})` sur le `Future` pour garantir **aucune** erreur asynchrone non gérée, même en cas de régression future dans `SessionApi`.

## Garanties sécurité / robustesse

| Sujet | Comportement |
|--------|----------------|
| Idempotence backend | Inchangée — toujours le même endpoint et les mêmes retries côté client. |
| Un seul ACK par succès PIN | Un seul `unawaited` par passage dans la branche succès (pas de boucle). |
| Exceptions | `SessionApi` absorbe déjà les erreurs ; `catchError` ajoute une barrière sur le `Future` racine. |
| Race « visible » | Navigation ne dépend plus du réseau ; l’ACK peut terminer après l’écran suivant — acceptable pour un signal de confort admin / progression. |

## Impact UX

- Navigation **sans attente réseau** après configuration du PIN.
- Aucun spinner ni message supplémentaire.
- Parcours signup / login / `PostLoginLocalSecurityFlow` / registration EU inchangés dans la structure (seul le non-blocage de l’ACK diffère).

## Limites restantes

- Si l’utilisateur tue l’app avant la fin des retries, l’ACK peut ne pas être enregistré (comportement déjà possible avec `await` long).
- Pas de file persistée : pas de reprise d’ACK au prochain cold start (hors scope de ce polish).

## Tests unitaires

- **Aucun test ajouté** : le changement est l’ordonnancement `await` → `unawaited` ; un test widget ou d’intégration devrait mocker `SessionApi` / canal réseau, ce que ce module ne facilite pas encore sans injection de dépendances.

## Raffinements futurs possibles

- **Queue persistée** (secure storage + worker au prochain `storeTokens` ou au resume) si le produit exige un taux de réussite serveur quasi 100 % malgré fermeture immédiate de l’app.
- **Client HTTP injectable** dans `SessionApi` pour tests et observabilité.

## Fichier modifié

- `mobile/lib/features/security/passcode/presentation/screens/passcode_setup_screen.dart`
