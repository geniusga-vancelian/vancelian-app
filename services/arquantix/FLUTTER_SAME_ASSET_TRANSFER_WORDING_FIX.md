# Flutter — Same-Asset Transfer Wording Fix

## Problème initial

Quand le wallet source utilise le même instrument que l'asset cible de l'offre
(ex: USDC → USDC), l'étape 1 affichait :

- Titre : **"Conversion"**
- Texte : **"Aucune conversion nécessaire"** + icône check grise

Ce wording est inexact : il n'y a pas de "non-conversion", il y a un transfert
direct depuis le wallet de l'utilisateur. Le terme "Conversion" est trompeur
dans ce contexte.

## Nouvelle règle UX

### Si `fundingAsset == entryAssetUsed` (same-asset)

| Champ | Valeur |
|-------|--------|
| Titre étape 1 | **Transfert** |
| Texte principal | **Depuis votre wallet {ASSET}** |
| Texte secondaire | **Aucun frais de transfert** |

### Si `fundingAsset != entryAssetUsed` (conversion)

| Champ | Valeur |
|-------|--------|
| Titre étape 1 | **Conversion** |
| Texte principal | **{amount} {source} → ≈ {amount} {target}** |
| Texte secondaire | **Montant estimé selon le prix de marché** |

## Wording final — 3 cas

### Cas A — Same-asset (USDC → USDC)

```
① Transfert
│  Depuis votre wallet USDC
│  Aucun frais de transfert
│
② Allocation
   1000.00 USDC alloués au programme de prêt
   Votre allocation sera affectée au programme
   selon le statut du produit
```

### Cas B — Fiat (EUR → USDC)

```
① Conversion
│  1 000,00 € → ≈ 1155.07 USDC
│  Montant estimé selon le prix de marché
│
② Allocation
   ≈ 1155.07 USDC alloués au programme de prêt
   Votre allocation sera affectée au programme
   selon le statut du produit
```

### Cas C — Crypto (BTC → USDC)

```
① Conversion
│  0.100000 BTC → ≈ 6838.92 USDC
│  Montant estimé selon le prix de marché
│
② Allocation
   ≈ 6838.92 USDC alloués au programme de prêt
   Votre allocation sera affectée au programme
   selon le statut du produit
```

## Logique conditionnelle

```dart
if (isSameAsset && !hasConversion) {
  step1 = TransactionStepItem(
    title: 'Transfert',
    primaryText: 'Depuis votre wallet ${entryAssetUsed}',
    secondaryText: 'Aucun frais de transfert',
  );
} else {
  step1 = TransactionStepItem(
    title: 'Conversion',
    primaryWidget: conversionRichText,
    secondaryText: 'Montant estimé selon le prix de marché',
    approximate: true,
  );
}
```

La condition est générique : fonctionne pour USDC, EURC, BTC, ou tout autre
asset identique entre source et cible.

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Logique preview | Inchangée |
| Logique invest | Inchangée |
| Composant DS TransactionStepsModule | Inchangé |
| LegalFooterNote | Inchangée |
| Navigation | Inchangée |
| Étape 2 wording | Inchangé |
| Flutter analyze | **0 issues** |

## Compilation

```
$ flutter analyze lending_invest_preview_screen.dart
No issues found!
```
