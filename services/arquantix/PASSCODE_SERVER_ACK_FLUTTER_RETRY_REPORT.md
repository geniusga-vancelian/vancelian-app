# Passcode — retry Flutter sur `POST /auth/security/local-passcode-ack`

## Point de départ

- Appel unique dans `SessionApi.ackLocalPasscodeRegistered` depuis `PasscodeSetupScreen` après succès du PIN.
- Les erreurs étaient entièrement absorbées (`catch` vide) pour ne pas interrompre le flux.
- Aucun retry : un échec transitoire (réseau, 503, timeout) laissait le backend sans `local_passcode_registered_at`.

## Stratégie de retry retenue

- **3 tentatives** au total : une immédiate, puis **2** nouvelles passes après de courts délais (backoff fixe).
- **Backoff** : 350 ms avant la 2ᵉ tentative, 700 ms avant la 3ᵉ (pas de backoff exponentiel pour rester minimal).
- **Timeout HTTP** : 8 s par tentative (évite qu’une socket bloquée retarde indéfiniment le retour vers l’UI).
- **Arrêt anticipé** : succès HTTP **2xx** → fin immédiate.
- **Pas de retry** si la réponse est **401** ou **403** (jeton ou droits invalides — les répétitions n’y changeraient rien).
- **Toute autre non-2xx** (5xx, 429, 404, etc.) : nouvelle tentative selon la limite ci-dessus.
- **Exceptions** (timeout, DNS, etc.) : nouvelle tentative jusqu’à épuisement, puis silence (comportement inchangé pour l’utilisateur).

## Nombre de tentatives et timing

| Étape | Déclencheur | Délai avant l’envoi |
|-------|----------------|----------------------|
| 1 | Immédiat | 0 ms |
| 2 | Après échec de la 1 | +350 ms |
| 3 | Après échec de la 2 | +700 ms |

Durée plafond théorique (toutes les tentatives en timeout) : ≈ 3 × 8 s + 1,05 s de backoff (cas extrême).

## Impact UX

- Aucun spinner ni message supplémentaire.
- Le flux PIN se termine comme avant ; en cas de succès rapide (cas nominal), **aucune attente** perceptible en plus d’un seul POST.
- Si le réseau est mauvais, l’utilisateur peut rester quelques centaines de ms à quelques secondes de plus sur l’écran de setup **avant** la navigation suivante (le `await` existant sur l’ACK dans `PasscodeSetupScreen` est conservé).

## Bonus « retry différé au prochain login »

- **Non implémenté** : éviter un état persistant (file d’attente, flag secure storage) et des effets de bord sur le login pour un gain marginal alors que l’endpoint est idempotent et les 3 tentatives couvrent déjà la majorité des pannes transitoires.

## Limites restantes

- Après 3 échecs consécutifs, le signal serveur peut toujours manquer jusqu’à une action ultérieure (ex. prochaine évolution produit avec file d’ACK).
- Les erreurs **401/403** ne sont pas retentées : comportement attendu (session expirée / compte sans `person_id`).

## Fichier modifié

- `mobile/lib/features/security/passcode/data/session_api.dart`

## Tests automatisés

- Pas de test unitaire ajouté : le module ne reçoit pas de client HTTP injectable ; le comportement est documenté ici. Une évolution possible serait d’extraire un `http.Client` ou une closure pour permettre des mocks.
