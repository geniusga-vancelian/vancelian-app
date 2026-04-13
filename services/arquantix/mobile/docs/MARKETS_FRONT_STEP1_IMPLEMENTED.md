# Markets Screen – Step 1 Implementation Note

## Objectif

Écran **Markets** (Crypto Markets) avec intégration données réelles : section Top Crypto branchée sur les APIs market-data du backend, section Crypto Bundles inchangée (vaults), Research et Latest News conservés.

## Fichiers créés

| Fichier | Rôle |
|--------|------|
| `lib/features/markets/data/market_data_api.dart` | Client REST : `getMarketSummary(symbols)`, `getTopMovers(limit)`. Modèles `MarketSummaryItem`, `TopMoversResponse`. |
| `lib/features/markets/data/market_display_utils.dart` | Mapper symbole → nom/ticker (ex. BTCUSDT → Bitcoin / BTC), `defaultPopularSymbols`, helpers `formatPrice`, `formatPercent`, `formatVolumeCompact`. |
| `docs/MARKETS_FRONT_STEP1_IMPLEMENTED.md` | Cette note. |

## Fichiers modifiés

| Fichier | Modifications |
|--------|----------------|
| `lib/core/config.dart` | Ajout `marketDataBaseUrl` (env `MARKET_DATA_BASE_URL` optionnel), `marketSummaryUrl`, `topMoversUrl`. |
| `lib/features/markets/presentation/screens/markets_screen.dart` | Section Top Crypto : chargement via `MarketDataApi` (market-summary + top-movers), états chargement / erreur / vide, pull-to-refresh, « See more » → `AllCryptoScreen`, tap row → `CryptoDetailScreen`. Suppression du `VaultsMarketingCardsFeed` pour top-crypto-widget. |
| `lib/features/markets/presentation/widgets/top_crypto_assets_module.dart` | Affichage « Aucune donnée » quand la liste de l’onglet actif est vide. |

## APIs utilisées

- **Populaires** : `GET /api/market-data/market-summary?symbols=BTCUSDT,ETHUSDT,...` (liste fixe `defaultPopularSymbols`).
- **Top Gainers / Top Losers** : `GET /api/market-data/top-movers?limit=10` ; on utilise `top_gainers` et `top_losers`.

Pas d’auth côté Flutter pour l’instant. Si le backend exige un token, il faudra ajouter un header (ex. `Authorization: Bearer ...`) dans `MarketDataApi`.

## Comportement des onglets

- **Populaires** : données de `market-summary` pour les symboles par défaut (BTC, ETH, SOL, XRP, BNB, ADA, DOGE, USDC).
- **Top Gainers** : `top_movers.top_gainers`.
- **Top Losers** : `top_movers.top_losers`.

Les données sont chargées une fois au premier affichage et au pull-to-refresh ; les trois jeux (popular, gainers, losers) sont mis en cache en mémoire pour la session. Pas d’appel dupliqué au changement d’onglet.

## États UI

- **Chargement** : carte blanche avec indicateur + texte « Chargement des marchés… ».
- **Erreur** : carte avec icône, message et bouton « Réessayer ».
- **Vide** (onglet sans données) : liste vide avec libellé « Aucune donnée » dans la carte.
- **Données** : liste d’assets (icône, nom, symbole, prix, variation 24h %).

## Limitations connues

- **Auth** : les routes backend `market-summary` et `top-movers` sont protégées (`AdminUser`). En l’état, l’appel depuis l’app peut renvoyer 401 ; à traiter côté backend (route publique ou token mobile) ou en ajoutant le token dans le client.
- **Base URL** : par défaut = `apiBaseUrl` (Next.js). Si l’API market-data est sur un autre host/port (ex. FastAPI sur 8011), définir `MARKET_DATA_BASE_URL` en build/run.
- **Sparkline** : `sparkline_24h` est présent dans `MarketSummaryItem` mais n’est pas affiché dans la row (prévu pour une itération ultérieure).
- **WebSocket** : pas implémenté ; le code est prêt pour ajouter un service/hook de mise à jour des prix en temps réel sans refonte de l’écran.

## Reporté volontairement

- WebSocket `/ws/market-data` pour mise à jour live des prix.
- Page détail asset avec graphique complet (candles) ; le tap ouvre l’existant `CryptoDetailScreen`.
- « See more » étendu (ex. filtre par catégorie) ; pour l’instant redirection vers `AllCryptoScreen`.
- Moteur de métadonnées complet pour les symboles ; mapper minimal dans `market_display_utils.dart`.

## Résumé

- **Créés** : `market_data_api.dart`, `market_display_utils.dart`, cette doc.
- **Modifiés** : `config.dart`, `markets_screen.dart`, `top_crypto_assets_module.dart`.
- **Onglets** : Populaires ← market-summary, Top Gainers / Top Losers ← top-movers.
- **À faire ensuite** : auth si requis, WebSocket optionnel, sparkline dans la row, base URL market-data en prod.
