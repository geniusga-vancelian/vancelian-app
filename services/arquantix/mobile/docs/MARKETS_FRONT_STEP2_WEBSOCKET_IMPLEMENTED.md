# Markets Screen – Step 2: WebSocket Live Prices

## Objectif

Mise à jour des prix en temps réel pour la liste Top Crypto via le WebSocket backend, sans refonte de l’écran ni du flux REST.

## Endpoint WebSocket

- **URL** : `WS /ws/market-data?symbols=BTCUSDT,ETHUSDT,...`
- **Base** : dérivée de `Config.marketDataBaseUrl` (http → ws, https → wss).
- **Format des messages** : `{"quotes": [{"symbol": "BTCUSDT", "price": 123.45, ...}]}` (envoyé environ toutes les 2 s côté backend).

## Fichiers créés

| Fichier | Rôle |
|--------|------|
| `lib/features/markets/data/market_data_ws_service.dart` | Service WebSocket : `subscribe(symbols, onQuotes)`, `disconnect()`. Parse les quotes, émet des `QuoteUpdate`. Retry simple (3 tentatives, 2 s d’écart) puis échec silencieux. |

## Fichiers modifiés

| Fichier | Modifications |
|--------|----------------|
| `pubspec.yaml` | Dépendance `web_socket_channel: ^3.0.0`. |
| `lib/core/config.dart` | `wsMarketDataBaseUrl` (http→ws, https→wss), `wsMarketDataUrl(symbolsQuery)`. |
| `lib/features/markets/presentation/screens/markets_screen.dart` | `MarketDataWsService`, `_selectedTopCryptoTab`, `_subscribeWsForCurrentTab()`, `_onWsQuotes()`, `_onTopCryptoTabChanged()`. Souscription après chargement REST ; mise à jour des listes (prix uniquement) ; `disconnect()` dans `dispose`. |
| `lib/features/markets/presentation/widgets/top_crypto_assets_module.dart` | Callback `onTabChanged(TopCryptoTab)` appelé à chaque changement d’onglet. |

## Comportement par onglet

- **Populaires** : souscription aux symboles de `_popularSummaries` (market-summary).
- **Top Gainers** : souscription aux symboles de `_topGainers`.
- **Top Losers** : souscription aux symboles de `_topLosers`.

Au changement d’onglet : déconnexion puis souscription aux symboles de l’onglet actif uniquement.

## Mise à jour des lignes

- Les messages WS contiennent `symbol` et `price`.
- On met à jour uniquement le `price` des `MarketSummaryItem` dont le `symbol` correspond ; `change_24h_pct` / `change_24h_abs` restent ceux du REST (pas de recalcul côté client).
- Un seul `setState` par batch de quotes pour limiter les rebuilds.

## Reconnexion

- En cas d’erreur ou de fermeture du WebSocket : jusqu’à 3 reconnexions avec 2 s d’intervalle, puis arrêt silencieux.
- Pas de bannière ni de message utilisateur pour les échecs WS ; l’affichage REST reste inchangé.

## Lifecycle

- **init** : pas de connexion WS avant la fin du chargement REST.
- **Après REST** : `addPostFrameCallback` → `_subscribeWsForCurrentTab()` (symboles de l’onglet actif, par défaut Populaires).
- **Changement d’onglet** : `onTabChanged` → `setState` + `addPostFrameCallback` → `_subscribeWsForCurrentTab()` (disconnect puis subscribe aux nouveaux symboles).
- **Pull-to-refresh** : rechargement REST puis même `addPostFrameCallback` → souscription mise à jour avec les nouvelles listes.
- **dispose** : `_wsService.disconnect()` (annule aussi les retries).

## Rafraîchissement toutes les 2 s

- Le **backend** envoie un message WS environ **toutes les 2 secondes** (lecture en base puis envoi).
- Les **valeurs** viennent de la table `market_data_latest_quotes`. Pour que les **taux affichés changent** vraiment, il faut lancer le worker **Binance WS ingestion** : `cd api && python3 scripts/run_binance_ws_ingestion.py`. Sans ce worker, le backend renverra les mêmes prix à chaque message.
- Côté Flutter : réception + `setState` via `addPostFrameCallback` (main isolate). En debug, les logs `[MarketDataWS] message #N` confirment la réception.

## Limitations

- Pas d’auth sur le WebSocket (aligné avec le backend V1).
- Les variations 24h ne sont pas recalculées depuis le WS (reste le dernier REST).
- Pas de gestion explicite app resume/pause (le WS peut se couper et sera retenté au prochain message ou au prochain refresh).
- Pas de sparkline ni de chart en temps réel.

## Résumé

- **Créé** : `market_data_ws_service.dart`.
- **Modifié** : `pubspec.yaml`, `config.dart`, `markets_screen.dart`, `top_crypto_assets_module.dart`.
- **Flux** : REST pour l’état initial et le refresh ; WS pour mettre à jour le prix des lignes visibles de l’onglet actif.
- **À faire plus tard** : auth WS si requis, recalcul optionnel du 24h à partir du WS, gestion explicite resume/pause.
