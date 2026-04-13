# Crypto Wallet Hero Chart — Asset-Scope Fix

## Executive Summary

Le chart sparkline du hero sur `CryptoWalletDetailScreen` affichait la **même courbe** pour tous les assets (BTC, ETH, SOL, etc.). Cause : l'appel `fetchHistory(period: 'ALL')` ne transmettait pas l'asset courant, chargeant systématiquement la série globale portefeuille.

Fix : **une seule ligne modifiée** — ajout de `asset: widget.asset` à l'appel `fetchHistory()`.

---

## Root Cause

### Code incriminé

```dart
// CryptoWalletDetailScreen._loadHeroSparkline() — AVANT
final data = await _historyApi.fetchHistory(period: 'ALL');
```

Aucun paramètre `asset` n'est transmis. La méthode `fetchHistory()` appelle :

```
GET /api/mobile/flutter/wallet/history?period=ALL
```

Sans `asset`, le backend charge **tous** les `exchange_orders` du client et reconstruit une série portefeuille global. Résultat : BTC, ETH, SOL affichent la même courbe identique.

### Chaîne complète du bug

```
CryptoWalletDetailScreen (BTC)
  → _historyApi.fetchHistory(period: 'ALL')              ← pas d'asset
  → GET /api/mobile/flutter/wallet/history?period=ALL     ← pas d'asset
  → GET /api/app/wallet/history?period=ALL                ← pas d'asset
  → build_wallet_history(db, client_id)                   ← charge TOUS les ordres
  → série = Σ all assets = courbe portefeuille global
```

Même flux pour ETH et SOL → même courbe → bug visuellement évident.

---

## Backend/API Usage

Le support `asset` est déjà en place sur toute la chaîne (implémenté lors du fix Statistics) :

| Couche | Endpoint | Paramètre asset |
|--------|----------|-----------------|
| Backend FastAPI | `GET /api/app/wallet/history?asset=BTC&period=ALL` | ✅ Supporté |
| Next.js proxy | `GET /api/mobile/flutter/wallet/history?asset=BTC&period=ALL` | ✅ Transmis |
| Flutter API | `fetchHistory(period: 'ALL', asset: 'BTC')` | ✅ Supporté |
| Config URL | `walletHistoryUrl('ALL', asset: 'BTC')` | ✅ Supporté |

Le hero chart n'utilisait tout simplement pas ce paramètre.

---

## Flutter Fix

### Fichier modifié

`mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart`

### Changement (1 ligne)

```dart
// AVANT
final data = await _historyApi.fetchHistory(period: 'ALL');

// APRÈS
final data = await _historyApi.fetchHistory(period: 'ALL', asset: widget.asset);
```

### Flux corrigé

```
CryptoWalletDetailScreen (BTC)
  → _historyApi.fetchHistory(period: 'ALL', asset: 'BTC')
  → GET /api/mobile/flutter/wallet/history?period=ALL&asset=BTC
  → GET /api/app/wallet/history?period=ALL&asset=BTC
  → build_wallet_history(db, client_id, asset='BTC')
  → série = position_BTC × price_BTC uniquement
```

### Pas de state partagé

Chaque `CryptoWalletDetailScreen` est une instance indépendante avec son propre `_heroSparkline`. Quand l'utilisateur navigue de BTC vers ETH, un nouvel écran est créé avec son propre state et son propre appel API. Aucun cache ou singleton n'interfère.

---

## Validation Scenarios

### Scénario 1 : BTC affiche une courbe différente de ETH

| Vérification | Attendu |
|-------------|---------|
| Page BTC → sparkline hero | Courbe basée sur position_BTC × price_BTC |
| Page ETH → sparkline hero | Courbe basée sur position_ETH × price_ETH |
| Les deux courbes sont visuellement différentes | ✅ (si historiques distincts) |

### Scénario 2 : ETH affiche une courbe différente de SOL

| Vérification | Attendu |
|-------------|---------|
| Page ETH → sparkline hero | Courbe ETH uniquement |
| Page SOL → sparkline hero | Courbe SOL uniquement |

### Scénario 3 : Cohérence avec le solde total

| Vérification | Attendu |
|-------------|---------|
| Dernier point du hero chart | ≈ Solde total affiché en gros |
| Forme de la courbe | Reflète l'historique de la position de cet asset |

### Scénario 4 : Dernier point = valeur affichée

| Vérification | Attendu |
|-------------|---------|
| `live_point.wallet_value` (backend) | = `position × live_price_eur` |
| Valeur affichée en haut (subtitle) | = `totalValueEur` de `CryptoWalletDetail` |
| Les deux sont alignés | ✅ (même source de prix) |

### Scénario 5 : Cohérence Statistics ↔ Hero

| Vérification | Attendu |
|-------------|---------|
| Hero chart BTC | Même série asset-scoped que Statistics BTC |
| Appel API identique | `fetchHistory(period: 'ALL', asset: 'BTC')` pour les deux |

---

## Fichier modifié

| Fichier | Modification |
|---------|-------------|
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Ajout `asset: widget.asset` à `fetchHistory()` dans `_loadHeroSparkline()` |

---

## Final Status

| Critère | Statut |
|---------|--------|
| BTC hero chart = série BTC uniquement | ✅ |
| ETH hero chart = série ETH uniquement | ✅ |
| SOL hero chart = série SOL uniquement | ✅ |
| Hero chart cohérent avec solde total | ✅ |
| Dernier point = live value | ✅ |
| Page Statistics non impactée | ✅ |
| Pas de refactoring de la page | ✅ |
| Réutilisation de la logique asset-scoped existante | ✅ |
