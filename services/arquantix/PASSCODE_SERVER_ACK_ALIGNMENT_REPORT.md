# Passcode — ACK serveur (`local-passcode-ack`)

## Problème initial

Le backend ne pouvait pas distinguer de façon fiable un PIN uniquement local (secure storage) d’un setup terminé **côté produit** sans signal serveur. `foundation.passcode_created` restait souvent `None`.

## Endpoint retenu

- **Méthode / chemin** : `POST /auth/security/local-passcode-ack`
- **Auth** : `Authorization: Bearer` (même modèle que le login mobile : `AdminUser` avec `person_id`).
- **Corps** : vide (pas de secret, pas de hash).
- **En-têtes optionnels** : `X-Device-ID` — stocké sous `profile_json.security.local_passcode_ack_device_id` (tronqué 128 car.), à titre de contexte non sensible.

## Réponse

```json
{
  "local_passcode_registered_at": "2026-04-03T12:00:00Z",
  "already_acknowledged": false
}
```

- **Idempotent** : si `profile_json.security.local_passcode_registered_at` existe déjà, réponse `200` avec `already_acknowledged: true` et le **même** horodatage (pas d’écrasement).

## Source de vérité backend

- `persons.profile_json.security.local_passcode_registered_at` — horodatage serveur (UTC, suffixe `Z`).
- Aucun stockage du PIN, aucun matériel cryptographique.

## Moment d’appel Flutter

- **`PasscodeSetupScreen`** : immédiatement après `PasscodeService.instance.setPasscode` et `setBiometricUnlockEnabled(false)`, si un access token est disponible (`SessionService.readAccessToken`).
- Implémentation : `SessionApi.ackLocalPasscodeRegistered` — erreurs réseau **avalées** pour ne pas bloquer l’UX (retry possible au prochain login si besoin).

## Impact sur `registration_progress`

- `foundation.passcode_created` : `True` dès que l’horodatage est présent (inchangé côté calcul, signal désormais **rempli** après ACK).
- **Libellé macro** `ACCOUNT_SECURED` : si `passcode_created is True`, libellé **« Compte sécurisé (mobile + PIN enregistré) »** au lieu de la variante mobile seule.

## Cas limites et retry

- Pas de session API : pas d’appel (comportement inchangé).
- Échec réseau : le flux PIN reste valide localement ; l’ACK pourra être rejoué manuellement ou lors d’une future évolution (ex. retry backoff) sans doublon grâce à l’idempotence.
- Compte sans `person_id` : `403` (`security.no_person_linked`).

## Fichiers

- Backend : `api/services/auth/local_passcode_ack_routes.py`, `api/main.py`
- Flutter : `mobile/lib/features/security/passcode/data/session_api.dart`, `passcode_setup_screen.dart`
- Tests : `api/tests/test_local_passcode_ack.py`
