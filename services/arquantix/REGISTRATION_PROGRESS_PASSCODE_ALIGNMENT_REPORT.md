# Registration progress — alignement passcode / `account_secured`

## Problème initial

La progression canonique s’appuyait sur des champs `profile_json.security` (ex. `passcode_set` / `passcode_enabled`) peu fiables : le passcode est une mécanique **locale** (secure storage, `PostLoginLocalSecurityFlow`), pas une vérité serveur systématique.

## Source de vérité retenue

- **Option hybride (B + A)** :
  - **`foundation.passcode_created`** : signal **serveur optionnel** uniquement — `True` si `profile_json.security.local_passcode_registered_at` est présent (ack horodaté), **`None`** si aucun signal (cas nominal : passcode uniquement local), **`False`** réservé si un endpoint marque explicitement l’absence (`local_passcode_ack is False`).
  - **`account_secured` (macro)** : ne dépend **plus** du passcode. Il représente **« mobile collecté + OTP SMS vérifié »** (aligné produit sur la sécurisation minimale côté compte avant KYC), cohérent avec le fait que le passcode n’est pas une obligation serveur.

## Modifications

- `api/services/customers_admin/registration_progress.py` : `_passcode_server_signal()`, libellé macro `ACCOUNT_SECURED`, liste `foundation:passcode_server_ack` pour l’ack optionnel.
- `api/services/customers_admin/schemas.py` : description du champ `passcode_created`.
- Tests : `test_mobile_otp_verified`, `test_passcode_server_ack_optional`.

## Impact sur `account_secured`

- Toujours atteignable dès que `mobile_verified` et `mobile_collected` sont vrais (challenge SMS vérifié + téléphone en profil).
- Pas de faux positif « compte sécurisé » basé sur un flag profil arbitraire.

## Impact login / signup

- Aucun changement de flux Flutter : pas de duplication du local security flow côté API.
- Si un jour un endpoint d’ack serveur est branché après `PasscodeSetupScreen`, le champ `local_passcode_registered_at` enrichira `passcode_created` sans changer la macro `account_secured`.

## Limites restantes

- Sans ack serveur, **`passcode_created` reste `None`** : c’est voulu (conservateur, pas d’inférence).
- Le backend ne sait pas si un appareil a un passcode local tant qu’aucun ack n’est écrit.
