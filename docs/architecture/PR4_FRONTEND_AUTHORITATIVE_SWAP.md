# PR4 — Front aligné sur le mode autoritaire / enqueue-and-wait

> Suite de PR2 (worker autoritaire) + PR3 (enqueue-and-wait). Le backend met déjà en file et
> exécute côté serveur ; le front voyait encore des 409 et donnait l'impression d'un échec.
> PR4 fait refléter au front la **vérité backend** : *confirmé = accepté dans la file, pas
> exécuté immédiatement*.

## Problème résolu

En mode autoritaire, les routes client (`/approval`, `/submit`, `/server-execute`) renvoient
`409 swap.server_authoritative`. Le front les appelait quand même → écran d'erreur, tentation de
re-cliquer. PR4 : après `confirm-execute`, le front **ne signe plus rien** et **poll le statut**.

## Changements backend (signaux, lecture seule)

| Fichier | Changement |
|---|---|
| `services/lifi/schemas.py` | `SwapConfirmExecuteResponse` : `server_authoritative`, `intent_id` ; `SwapStatusResponse` : `server_authoritative`, `queue_state` |
| `services/lifi/swap_queue_state.py` *(nouveau)* | `compute_swap_queue_state` : statut swap (+ slot global) → `waiting_for_previous` / `preparing` / `executing` / `confirming` / `completed` / `failed` |
| `services/swap_core/confirm_poll.py` | `confirm-execute` renvoie `server_authoritative` + `intent_id` |
| `services/lifi/lifi_execute_service.py` | `get_status` calcule `server_authoritative` + `queue_state` (les autres appelants gardent les défauts) |

`queue_state` (pré-exécution) :
- un **autre** intent détient le slot user → `waiting_for_previous` (le swap est en file) ;
- sinon → `preparing`.
- `BROADCASTING` → `executing` ; `SUBMITTED` → `confirming` ; `CONFIRMED` → `completed` ; `FAILED/EXPIRED` → `failed`.

## Changements front (`services/arquantix/web`)

| Fichier | Changement |
|---|---|
| `lib/portal/swapClient.ts` | Types `server_authoritative` / `intent_id` / `queue_state` ; `SwapServerAuthoritativeError` ; 409 `swap.server_authoritative` / `transaction_in_progress` → erreur typée (bascule suivi) |
| `lib/portal/swapFlowTypes.ts` | Phases `queued` / `server_executing` / `confirming` |
| `components/portal/transaction/mappers/swapSteps.ts` | Stepper autoritaire 6 étapes + `swapAuthoritativeStepperIndex` |
| `components/portal/transaction/mappers/swapUiCopy.ts` | Copy file : titre, lead « accepté », lead « en attente d'une opération en cours » |
| `components/portal/swap/useLifiSwapExecution.ts` | `pollAuthoritativeUntilTerminal` (mappe `queue_state` → phase, fenêtre 25 min, sondage 6 s) |
| `components/portal/swap/PortalSwapExecutionController.tsx` | Après confirm : si `server_authoritative` → **pas** de signature client, suivi serveur ; gestion `SwapServerAuthoritativeError` ; stepper autoritaire |
| `components/portal/swap/PortalSwapReviewStep.tsx` | Bouton « Confirmer » désactivé après clic (anti double-clic) |

## Écran d'étapes (vérité backend)

1. **Demande reçue** — accepté + placé en file
2. **En attente d'une opération en cours** — `waiting_for_previous` (banni­ère : « Une autre opération financière est en cours. Votre échange démarrera automatiquement… »)
3. **Préparation de l'échange** — `preparing`
4. **Exécution on-chain** — `executing`
5. **Confirmation de la transaction** — `confirming`
6. **Terminé** — `completed`

Pour le 1er swap, l'étape 2 passe vite ou n'apparaît pas. Pour un 2e swap lancé pendant le 1er,
l'utilisateur voit clairement l'attente en file — pas de doute, pas de retry, pas de panique.

## Non inclus (volontairement)

- Pas de PR/flow rebalancing, DCA, multi-leg (les legs bundle réutilisent le même hook mais
  **sans** le chemin autoritaire — hors périmètre).
- Pas d'activation de flags supplémentaires : PR4 est purement client + signaux backend
  rétro-compatibles (champs par défaut `false` / `null` hors mode autoritaire).

## Validation

- Backend : `test_swap_authoritative_status_pr4.py` (6/6) + suites PR2/PR3/worker/e2e/routes vertes.
- Front : `tsc --noEmit` → 0 erreur.

### Test utilisateur naturel (après déploiement)

1. Je clique « Confirmer l'échange » → l'app affiche **« Échange en file de traitement »** (plus de 409).
2. J'attends → étapes Préparation → Exécution → Confirmation.
3. L'app affiche **succès**.
4. Deux swaps rapides → le 2e affiche **« En attente d'une opération en cours »** puis démarre seul.

> Latence : le worker tourne par ticks (~10 min). Le suivi front tolère jusqu'à 25 min ; au-delà,
> message non bloquant « l'échange peut encore aboutir ».
