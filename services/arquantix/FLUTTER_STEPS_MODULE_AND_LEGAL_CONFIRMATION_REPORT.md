# Flutter — TransactionStepsModule + LegalFooterNote + Wording juridique

## Résumé

Extraction du widget local `_ExclusiveOfferInvestStepsCard` en deux composants
officiels du Design System, réutilisables et configurables en JSON/CMS :

1. **`TransactionStepsModule`** — carte blanche avec timeline verticale
2. **`LegalFooterNote`** — note de conformité bas de page avec liens cliquables

Mise à jour du wording de l'étape 2 pour plus de précision juridique.

---

## Nouveaux composants DS

### TransactionStepsModule

**Fichier** : `lib/design_system/components/transaction_steps_module.dart`

Carte blanche avec :
- Titre configurable
- Timeline verticale (cercles numérotés + ligne 2px `AppColors.border`)
- N étapes avec titre, texte principal (String ou Widget), texte secondaire
- Support de l'état (`pending`, `active`, `completed` → icône check)
- Ombre légère DS

**API** :

```dart
TransactionStepsModule(
  title: 'Étapes de votre investissement',
  steps: [
    TransactionStepItem(
      number: 1,
      title: 'Conversion',
      primaryWidget: myRichText,
      secondaryText: 'Montant estimé selon le prix de marché',
    ),
    TransactionStepItem(
      number: 2,
      title: 'Allocation',
      primaryWidget: myRichText,
      secondaryText: '...',
    ),
  ],
)
```

**JSON CMS** :

```json
{
  "type": "transactionSteps",
  "title": "Étapes de votre investissement",
  "steps": [
    {
      "number": 1,
      "title": "Conversion",
      "primaryText": "0.100000 BTC → ≈ 6790.58 USDC",
      "secondaryText": "Montant estimé selon le prix de marché"
    },
    {
      "number": 2,
      "title": "Allocation",
      "primaryText": "≈ 6790.58 USDC alloués au programme de prêt",
      "secondaryText": "Votre allocation sera affectée au programme selon le statut du produit"
    }
  ]
}
```

---

### TransactionStepItem

**Fichier** : `lib/design_system/components/transaction_step_item.dart`

Modèle de données pour une étape transactionnelle :

| Champ | Type | Description |
|-------|------|-------------|
| `number` | `int` | Numéro d'étape (1, 2, …) |
| `title` | `String` | Titre (ex: "Conversion") |
| `primaryText` | `String?` | Texte principal (ignoré si `primaryWidget` fourni) |
| `primaryWidget` | `dynamic` | Widget custom (Text.rich, Row, etc.) |
| `secondaryText` | `String?` | Sous-texte explicatif |
| `approximate` | `bool` | Flag ≈ (pour logique appelante) |
| `state` | `TransactionStepState` | `pending` / `active` / `completed` |
| `iconData` | `int?` | Code point icône optionnel |

Supporte `fromJson` / `listFromJson` pour compatibilité CMS.

---

### LegalFooterNote

**Fichier** : `lib/design_system/components/legal_footer_note.dart`

Note de conformité discrète avec segments de texte (plain ou lien) :

```dart
LegalFooterNote(
  segments: [
    LegalTextSegment(text: 'En confirmant, vous acceptez les '),
    LegalTextSegment(text: 'Conditions générales', url: 'https://...'),
    LegalTextSegment(text: ' applicables.'),
  ],
)
```

- Style : `bodySmall`, fontSize 12, `textSecondary`
- Liens : `AppColors.indigo`, underline, `TapGestureRecognizer` → `url_launcher`
- Supporte `fromJson` pour compatibilité CMS

**JSON CMS** :

```json
{
  "type": "legalFooterNote",
  "segments": [
    { "text": "En confirmant, vous acceptez les " },
    { "text": "Conditions générales", "url": "https://arquantix.com/legal" }
  ]
}
```

---

## Wording — Avant / Après

### Étape 2 — Allocation

| Aspect | Avant | Après |
|--------|-------|-------|
| Texte principal | "≈ 6790.58 USDC investis dans l'offre" | "≈ 6790.58 USDC **alloués au programme de prêt**" |
| Sous-texte | "Génère du rendement selon le statut du produit" | "Votre allocation sera affectée au programme selon le statut du produit" |

### Module bas de page (nouveau)

"En confirmant, vous reconnaissez que cette opération comprend une conversion
éventuelle puis une allocation à un programme de prêt en USDC lié à cette offre.
Consultez les **Conditions générales** avant de confirmer."

- Le texte est dynamique : la clause "conversion éventuelle" disparaît pour les
  investissements directs (USDC → USDC).
- "Conditions générales" est un lien cliquable.

---

## Rendu final

### Cas conversion (BTC → USDC)

```
┌──────────────────────────────────────┐
│ Étapes de votre investissement       │
│                                      │
│ ① Conversion                         │
│ │  0.10 BTC → ≈ 6790.58 USDC        │
│ │  Montant estimé selon le prix      │
│ │  de marché                         │
│ │                                    │
│ ② Allocation                         │
│    ≈ 6790.58 USDC alloués au         │
│    programme de prêt                 │
│    Votre allocation sera affectée    │
│    au programme selon le statut      │
│    du produit                        │
└──────────────────────────────────────┘

En confirmant, vous reconnaissez que cette
opération comprend une conversion éventuelle
puis une allocation à un programme de prêt en
USDC lié à cette offre. Consultez les
Conditions générales avant de confirmer.
```

### Cas direct (USDC → USDC)

```
┌──────────────────────────────────────┐
│ Étapes de votre investissement       │
│                                      │
│ ① Conversion                         │
│ │  ✓ Aucune conversion nécessaire    │
│ │                                    │
│ ② Allocation                         │
│    1000.00 USDC alloués au           │
│    programme de prêt                 │
│    Votre allocation sera affectée    │
│    au programme selon le statut      │
│    du produit                        │
└──────────────────────────────────────┘

En confirmant, vous reconnaissez que cette
opération comprend une allocation à un
programme de prêt en USDC lié à cette offre.
Consultez les Conditions générales avant
de confirmer.
```

---

## Fichiers

| Fichier | Action |
|---------|--------|
| `lib/design_system/components/transaction_step_item.dart` | **Nouveau** — modèle DS |
| `lib/design_system/components/transaction_steps_module.dart` | **Nouveau** — widget DS |
| `lib/design_system/components/legal_footer_note.dart` | **Nouveau** — widget DS |
| `lib/design_system/components/components.dart` | **Modifié** — exports ajoutés |
| `lending_invest_preview_screen.dart` | **Modifié** — utilise composants DS |

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Logique preview | Inchangée |
| Endpoints backend | Inchangés |
| Logique invest | Inchangée |
| Navigation | Inchangée |
| CTA "Confirmer l'investissement" | Inchangé |
| Processing / Success sheets | Inchangés |
| Flutter analyze | **0 issues** |

---

## Compilation

```
$ flutter analyze (5 fichiers)
No issues found!
```
