# Auto Execution Engine — Ordres Limit / Stop

## Architecture

Le moteur d'exécution automatique réutilise 100% de l'infrastructure existante du **PriceAlertEngine** sans nouvelle table. Les ordres sont des `price_alerts` avec `action_type = "order"` et un `order_payload` structuré en JSONB.

```
PriceTick → PriceAlertEngine → _trigger_single()
    ↓ (if action_type == "order")
    _execute_order_hook()
    ↓
    ExchangeService.buy() / .sell()
    ↓
    execution_status = "executed" | "failed"
```

## Types d'ordres

| Type       | Side | Order Type | Direction | Price Source |
|------------|------|------------|-----------|-------------|
| BUY LIMIT  | buy  | limit      | down      | ask         |
| BUY STOP   | buy  | stop       | up        | ask         |
| SELL LIMIT | sell | limit      | up        | bid         |
| SELL STOP  | sell | stop       | down      | bid         |

Le mapping direction/price_source est automatique et dérivé de `side` + `order_type` à la création.

## Fichiers modifiés / créés

### Backend

| Fichier | Action | Description |
|---------|--------|-------------|
| `api/services/price_alerts/engine.py` | Modifié | `_execute_order_hook` implémenté : appel `ExchangeService.buy()/sell()`, vérification slippage, mise à jour `execution_status` |
| `api/services/price_alerts/orders_router.py` | Créé | Endpoints `POST/GET/DELETE /api/app/orders` avec mapping automatique direction/price_source |
| `api/services/price_alerts/__init__.py` | Modifié | Export du `orders_router` |
| `api/main.py` | Modifié | Enregistrement du `orders_router` |

### Proxy Next.js

| Fichier | Action |
|---------|--------|
| `web/src/app/api/mobile/flutter/orders/route.ts` | Créé (GET + POST) |
| `web/src/app/api/mobile/flutter/orders/[orderId]/route.ts` | Créé (DELETE) |

### Flutter

| Fichier | Action | Description |
|---------|--------|-------------|
| `mobile/lib/core/config.dart` | Modifié | Ajout `ordersUrl` et `orderDeleteUrl` |
| `mobile/lib/features/alerts/domain/models/trigger_order.dart` | Créé | Modèle `TriggerOrder` avec `side`, `orderType`, `amount`, `slippageBps`, `executionPrice`, etc. |
| `mobile/lib/features/alerts/data/trigger_orders_api.dart` | Créé | Client API `TriggerOrdersApi` (create, list, cancel) |
| `mobile/lib/features/alerts/presentation/screens/orders_list_screen.dart` | Créé | Liste des ordres filtré par asset, cards avec status badges et distance % |
| `mobile/lib/features/alerts/presentation/screens/create_order_bottom_sheet.dart` | Créé | Bottom sheet : segmented BUY/SELL + LIMIT/STOP, prix cible, montant, slippage optionnel |
| `mobile/lib/features/markets/presentation/screens/crypto_detail_screen.dart` | Modifié | Ajout icône ordres dans la navbar |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Modifié | Ajout icône ordres dans la navbar |

## Hook d'exécution (`_execute_order_hook`)

Logique :

1. Lecture du `order_payload` (side, amount, slippage_bps)
2. Construction d'un `ExchangeBuyRequest` ou `ExchangeSellRequest` avec `external_reference = "trigger-{alert_id}-{random}"`
3. Appel `ExchangeService().buy()` ou `.sell()` avec `ActorContext(actor_type="trigger_engine")`
4. Si le résultat n'est pas `status=completed` → `execution_status = "failed"` avec raison
5. Vérification du slippage si `slippage_bps` est défini : compare `execution_price` vs `target_price`
6. Si slippage dépassé → `execution_status = "failed"` avec détails
7. Si succès → `execution_status = "executed"`, stockage du prix d'exécution et de l'order_id dans `metadata_`

## Idempotence

- L'alerte est verrouillée via `FOR UPDATE SKIP LOCKED` avant traitement
- Le status est vérifié (`active` → `triggered`) avant exécution
- L'`external_reference` est unique par exécution (UUID partiel), ce qui empêche l'`ExchangeService` de créer des doublons
- `execution_status` est passé à `pending` avant l'appel, puis mis à jour atomiquement

## Métriques

Les compteurs suivants sont incrémentés :
- `orders_executed` — exécution réussie
- `orders_failed` — exécution échouée (slippage, erreur exchange, etc.)

## Protection slippage

Optionnelle (0-500 bps, soit 0%-5%). Si activée :
- Compare le prix d'exécution réel au prix cible (trigger_price)
- Si l'écart en basis points dépasse le seuil → ordre échoué
- Le détail du slippage est stocké dans `metadata_` pour audit

## API

### `POST /api/app/orders`
Crée un ordre auto-exécuté. Body :
```json
{
  "asset": "BTC",
  "side": "buy",
  "order_type": "limit",
  "trigger_price": 65000.0,
  "amount": 100.0,
  "slippage_bps": 50
}
```

### `GET /api/app/orders?asset=BTC&status=active`
Liste les ordres de l'utilisateur, filtré par asset et/ou status.

### `DELETE /api/app/orders/{id}`
Annule un ordre actif.

## UX Flutter

### Création d'ordre (Bottom Sheet)
1. Segmented BUY (vert) / SELL (rouge)
2. Segmented LIMIT / STOP
3. Prix cible avec distance % live
4. Montant (EUR pour buy, crypto pour sell)
5. Protection slippage optionnelle (checkbox + input %)
6. Résumé contextuel expliquant la logique de déclenchement
7. Bouton de validation avec animation

### Liste des ordres
- Cartes avec type d'ordre, prix cible, montant, slippage
- Badge de status (Actif, Exécuté, Échoué, Annulé, Déclenché)
- Distance % au prix cible pour les ordres actifs
- Actions : annuler (X), confirmation modale

### Navigation
- Icône `swap_vert` ajoutée dans la navbar de chaque écran instrument et wallet
- Ordres scopés par instrument (comme les alertes)

## Extensions futures

- OCO (One Cancels Other)
- Trailing stop
- Partial fill / retry
- Smart routing multi-exchange
