# Flutter — Preview Header UX Refinement

## Changements appliqués

### 1. Navbar — alignement DS

**Avant** : header custom avec `BundleFlowHeaderDisk` + `Text('Confirmation')`
positionné manuellement dans un `Row` avec `Spacer`.

**Après** : `AppTopNavBar` — le composant DS officiel utilisé sur toutes les
pages de l'application. Configuré en mode `back` avec titre centré.

```dart
appBar: AppTopNavBar(
  leadingType: AppTopNavBarLeading.back,
  title: 'Confirmation',
  onBackTap: () => Navigator.of(context).pop(),
),
```

Gains :
- Style titre = `AppTypography.sectionTitle` (cohérent avec tout l'app)
- Disque retour = standard 36px avec ombre DS
- Espacement et hauteur gérés par le composant
- Plus besoin de `SafeArea` manuelle pour le top

### 2. Sous-texte enrichi

**Avant** : `"dans Dubai, Al Barari"`

**Après** : `"dans l'offre exclusive Dubai, Al Barari"`

Clarifie la nature du produit côté client sans jargon technique.

### 3. Équivalent EUR approximatif

**Ajouté** : une ligne `≈ X €` entre le montant principal et le sous-texte projet,
affichée uniquement quand le funding asset n'est pas EUR.

Hiérarchie visuelle finale :

```
Vous êtes sur le point d'investir

0.100000 BTC

≈ 6 834,73 €

dans l'offre exclusive Dubai, Al Barari
```

**Logique d'affichage** :

| Funding asset | Ligne EUR | Raison |
|--------------|-----------|--------|
| BTC | `≈ 6 834,73 €` | Approximation via USDC (pool asset) |
| USDC | `≈ 1 000,00 €` | USDC ≈ EUR |
| EUR | *Masquée* | Redondant (déjà en EUR) |

La valeur est dérivée de `estimatedPoolAssetAmount` (USDC ≈ USD ≈ EUR),
clairement marquée comme approximative avec `≈`.

### 4. CTA — radius DS

**Avant** : `BorderRadius.circular(16)` — hardcodé.

**Après** : `BorderRadius.circular(AppRadius.button)` — token DS (20px).

---

## Avant / Après

### Avant

```
┌─ [←] ─── Confirmation ──────────┐  ← custom Row
│                                   │
│ Vous êtes sur le point d'investir │
│                                   │
│ 0.100000 BTC                      │
│                                   │
│ dans Dubai, Al Barari              │
│                                   │
│ ┌─── Étapes ──────────────────┐   │
│ │ ...                         │   │
│ └─────────────────────────────┘   │
│                                   │
│ [← ] [ Confirmer l'investissement]│  ← radius 16
└───────────────────────────────────┘
```

### Après

```
┌─ AppTopNavBar: Confirmation ─────┐  ← DS component
│                                   │
│ Vous êtes sur le point d'investir │
│                                   │
│ 0.100000 BTC                      │
│ ≈ 6 834,73 €                      │  ← NEW
│                                   │
│ dans l'offre exclusive Dubai, ...  │  ← enrichi
│                                   │
│ ┌─── Étapes ──────────────────┐   │
│ │ ...                         │   │
│ └─────────────────────────────┘   │
│                                   │
│ [← ] [ Confirmer l'investissement]│  ← AppRadius.button
└───────────────────────────────────┘
```

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Module blanc des étapes | Inchangé |
| LegalFooterNote | Inchangée |
| Logique preview | Inchangée |
| Logique invest | Inchangée |
| Endpoints backend | Inchangés |
| Navigation | Inchangée |
| Flutter analyze | **0 issues** |

---

## Compilation

```
$ flutter analyze lending_invest_preview_screen.dart
No issues found!
```
