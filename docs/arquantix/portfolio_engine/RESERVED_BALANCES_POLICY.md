# Reserved Balances Policy (cadrage Phase 1)

## Contexte

Avec l’exécution on-chain (LI.FI), une opération peut rester longtemps dans un état non final. Sans réservation, le client peut :

- lancer un retrait sur des fonds déjà engagés dans un rebalance ;
- déclencher un second rebalance ou un swap utilisateur en parallèle ;
- provoquer un **double spend logique** entre sous-comptabilité PE et wallet Privy.

## Champ existant

`pe_position_atoms` expose déjà :

- `quantity`
- `available_quantity`
- `locked_quantity`

Phase 1 : **aucune politique cross-opérations n’est appliquée** ; ce document fixe le cadrage Phase 4.

## Lifecycle swap / rebalance (futur)

| État | Description |
|------|-------------|
| `QUOTE_RECEIVED` | Quote LI.FI valide, montant réservé logiquement |
| `SIGNATURE_REQUESTED` | Payload prêt côté client |
| `SIGNED` | Tx signée, pas encore soumise |
| `SUBMITTED` | Tx en mempool |
| `PENDING_CONFIRMATION` | Attente confirmations |
| `CONFIRMED` | Settlement on-chain → mise à jour atoms |
| `FAILED` | Libération réservation |
| `EXPIRED` | Libération réservation |

## Règle cible (Phase 4)

```text
available_quantity = quantity - locked_quantity - pending_outgoing_quantity
```

- `locked_quantity` : réservations explicites (rebalance batch, vault lock, mandat)
- `pending_outgoing_quantity` : somme des legs en cours non confirmés (table dédiée ou metadata swap)

## Règles métier

1. **Pas de crédit spot atom** avant `CONFIRMED` on-chain (aligné PRD Phase 1).
2. Toute leg `execute_leg` en statut `pending` doit créer une réservation sur le cash leg ou l’asset source.
3. Retraits et swaps user consultent `available_quantity` agrégé **et** solde Privy disponible.
4. Un seul rebalance actif par `portfolio_id` bundle à la fois (verrou optimiste ou réservation batch).

## Tables envisagées (Phase 4)

- `pe_balance_reservations` : `id`, `client_id`, `portfolio_id`, `instrument_id`, `amount`, `reference_type`, `reference_id`, `status`, `expires_at`
- Lien optionnel vers `person_wallet_swaps.id`

## Non-objectifs Phase 1

- Pas d’implémentation des réservations
- Pas de blocage des retraits
- Audit uniquement de `locked_quantity` usage actuel (reste à 0 en pratique sur bundles)
