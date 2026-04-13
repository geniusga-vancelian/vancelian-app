# Synchro des logos crypto (CoinGecko)

Système minimal pour télécharger et afficher les logos des actifs crypto via CoinGecko.

## Fichiers créés / modifiés

### Backend (API)

| Fichier | Modification |
|--------|---------------|
| `api/database.py` | Colonne `logo_filename` (String 100, nullable) sur `MarketDataInstrument`. |
| `api/alembic/versions/021_add_logo_filename_to_market_data_instruments.py` | Migration Alembic pour la colonne. |
| `api/scripts/sync_crypto_logos_coingecko.py` | **Créé** – script de synchro CoinGecko. |
| `api/services/market_data/routes.py` | `logo_url` ajouté aux réponses `all-crypto`, `market-summary`, `top-movers`. |

### Flutter (mobile)

| Fichier | Modification |
|--------|---------------|
| `mobile/lib/features/markets/data/all_crypto_api.dart` | `AllCryptoItem.logoUrl` + parsing `logo_url`. |
| `mobile/lib/features/markets/data/market_data_api.dart` | `MarketSummaryItem.logoUrl` + parsing. |
| `mobile/lib/features/markets/presentation/screens/all_crypto_screen.dart` | Avatar : logo réseau si `logoUrl` présent, sinon lettre + couleur. |
| `mobile/lib/features/markets/presentation/screens/markets_screen.dart` | `_summaryToAsset` et mise à jour WS : passage de `logoUrl` à `CryptoAssetItem`. |
| `mobile/lib/features/markets/presentation/widgets/top_crypto_assets_module.dart` | `CryptoAssetItem.logoUrl` + passage à `TransactionAvatar`. |
| `mobile/lib/ui/components/transaction/transaction_avatar.dart` | Paramètre optionnel `imageUrl` : affiche l’image si présent, sinon icône. |

## Lancer la synchro

Depuis la racine du repo ou depuis `api/` :

```bash
cd services/arquantix/api
python -m scripts.sync_crypto_logos_coingecko
```

Options :

- **Sans option** : ne re-télécharge pas si le fichier existe déjà ; met à jour la base si le fichier est déjà présent mais pas encore enregistré.
- **`--force`** : re-télécharge tous les logos même s’ils existent déjà.

Prérequis : migration 021 appliquée (`alembic upgrade head`), dépendances installées (`httpx` dans `requirements.txt`).

## Où sont stockés les logos

- **Côté serveur** : `api/uploads/crypto_logos/` (ex. `btc.png`, `eth.png`).
- **URL** : le backend renvoie un **chemin relatif** dans `logo_url` (ex. `/media/crypto_logos/btc.png`) pour que le client Flutter préfixe avec sa base API (`marketDataBaseUrl`). Ainsi les images se chargent depuis le même hôte que l’API (évite que `localhost` côté backend soit inaccessible depuis l’appareil/simulateur).

## Comportement si logo manquant

- **Script** : actif non matché sur CoinGecko → skip + log ; pas de `logo_filename` en base.
- **API** : si `logo_filename` est null, le champ `logo_url` est absent ou null dans les réponses.
- **Flutter** :
  - **All Crypto** : si `logoUrl` est null ou vide → avatar avec première lettre du ticker + couleur (comportement actuel).
  - **Top Crypto** : si `logoUrl` est null ou vide → `TransactionAvatar` affiche l’icône par défaut (bitcoin) sur fond coloré.

Aucun changement de design : fallback = placeholder/avatar existant.
