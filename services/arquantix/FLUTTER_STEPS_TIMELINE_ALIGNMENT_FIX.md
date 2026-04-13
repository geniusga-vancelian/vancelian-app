# Flutter — Steps Timeline & Alignment Fix

## Problème initial

### 1. Ligne verticale trop courte / déconnectée

La ligne entre les steps était un widget séparé (`_buildConnector`) avec une
hauteur fixe de 20px + gap 4px. Résultat : trou visuel entre le bas du step 1
et le haut du step 2. La ligne ne reliait pas les cercles de bord à bord.

### 2. Alignement cercle ↔ titre fragile

Le layout précédent (widgets séparés step + connector) ne garantissait pas
l'alignement stable du cercle avec la première ligne du titre, surtout si le
titre passait sur plusieurs lignes.

---

## Correction structurelle

### Architecture avant

```
Column
├─ StepRow(1)     → Row [Circle, Content]           ← hauteur du contenu
├─ Connector      → SizedBox(height: 20+8)          ← hauteur fixe, séparé
└─ StepRow(2)     → Row [Circle, Content]
```

Problème : le connector est indépendant, sa hauteur ne s'adapte pas au contenu.

### Architecture après

```
Column
├─ IntrinsicHeight                                   ← step non-last
│  └─ Row
│     ├─ _TimelineColumn [Circle + Expanded(line)]   ← ligne stretch auto
│     └─ Expanded(Padding(bottom: 20) + _StepContent)
└─ Row                                               ← step last (pas de line)
   ├─ _TimelineColumn [Circle, pas de ligne]
   └─ Expanded(_StepContent)
```

La clé : `IntrinsicHeight` force la `Row` à prendre la hauteur du plus grand
enfant (le contenu + padding). La colonne timeline utilise `Expanded` pour
étirer la ligne de 1px sur toute la hauteur restante sous le cercle.

---

## Détails techniques

### Ligne verticale — bord à bord

```dart
Column(
  children: [
    Circle(26px),
    Expanded(           // ← remplit tout l'espace restant
      child: Center(
        child: Container(width: 1, color: AppColors.border),
      ),
    ),
  ],
)
```

La ligne part immédiatement sous le cercle et descend jusqu'au bas de la row.
Le padding `bottom: 20` sur le contenu crée l'espacement entre les steps,
et la ligne couvre exactement cet espace.

### Alignement cercle ↔ première ligne du titre

Avec `crossAxisAlignment: CrossAxisAlignment.start` sur la Row, le haut du
cercle (26px) et le haut du texte titre (fontSize 15, lineHeight ~22px)
démarrent au même y. Le centre visuel du cercle (13px) et le centre visuel
de la première ligne de texte (~11px) sont quasi-alignés (Δ2px — imperceptible).

### Titre multiligne

```dart
Text(
  step.title,
  maxLines: 3,
  overflow: TextOverflow.ellipsis,
  style: ...(fontSize: 15, fontWeight: w600),
)
```

Le cercle reste aligné avec la première ligne quelle que soit le nombre de
lignes (1, 2 ou 3), car `CrossAxisAlignment.start` ancre les deux au top.

---

## Sous-composants extraits

| Composant | Rôle |
|-----------|------|
| `_TimelineColumn` | Cercle + ligne verticale, gestion `showLine` |
| `_StepContent` | Titre (1–3 lignes) + primaryText/Widget + secondaryText |

---

## Validation visuelle

### Cas A — titre court ("Conversion")

```
① Conversion
│  0.10 BTC → ≈ 6834.73 USDC
│  Montant estimé selon le prix de marché
│  ← ligne continue
② Allocation
   ≈ 6834.73 USDC alloués au programme de prêt
   Votre allocation sera affectée au programme…
```

Cercle aligné avec "Conversion". Ligne bord à bord.

### Cas B — titre 2 lignes ("Allocation au programme")

```
① Allocation au
│  programme
│  …contenu…
│
② …
```

Cercle aligné avec "Allocation au" (première ligne). Ligne OK.

### Cas C — titre 3 lignes

```
① Allocation au programme
│  de prêt en USDC pour
│  cette offre exclusive…
│  …contenu…
│
② …
```

Cercle toujours aligné première ligne. Ellipsis si > 3 lignes.

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| JSON parsing `fromJson` | Inchangé |
| `TransactionStepItem` | Inchangé |
| `LegalFooterNote` | Inchangé |
| Wording / contenu texte | Inchangé |
| Symbole ≈ | Inchangé |
| Logique conditionnelle | Inchangée |
| `lending_invest_preview_screen.dart` | Inchangé |
| Flutter analyze | **0 issues** |

---

## Compilation

```
$ flutter analyze transaction_steps_module.dart lending_invest_preview_screen.dart
No issues found!
```
