# FundingModule (Vault Builder)

## Rôle

Afficher un bloc « financement » (progression, taux, objectif) **uniquement** lorsque le module `FundingModule` est présent dans le JSON Vault pour la locale éditée. Il remplace l’ancien bandeau financement **injecté automatiquement** depuis le lending (retiré du rendu web).

## JSON (`content`)

| Champ | Description |
|--------|-------------|
| `title` | Titre optionnel au-dessus du bloc (éditorial, par locale). |
| `displayMode` | `auto_product` : valeurs lues depuis le **lending** côté serveur au rendu. `manual` : valeurs dans `manual`. |
| `items` | Lignes configurables : `key` ∈ `progress` \| `apr` \| `target`, `label` (éditorial), `enabled`. |
| `manual` | Si `displayMode === 'manual'` : `progressPct` (0–100), `rateDisplay`, `totalDisplay` (texte libre). |
| `footnote` | Markdown optionnel sous le bloc. |

Le serveur ajoute **`_resolved`** (non éditable) : `{ progressPct, rateDisplay, totalDisplay }` pour le front. Rien n’est dupliqué en base : en `auto_product`, les chiffres viennent du snapshot lending existant.

## Comportement

- **Sans module** dans le Vault → aucun bloc Funding.
- **`auto_product` sans lending** → `_resolved` absent → rien n’est affiché.
- **`manual`** → affichage à partir de `manual` + labels `items`.
- **Format APR** : formatage numérique selon la locale de la page (`fr` : virgule décimale).

## Différence avec l’ancien bloc automatique

Auparavant, le lending alimentait un composant hors liste de modules. Désormais, l’éditeur **place** explicitement un `FundingModule` et choisit le mode ; pas d’affichage implicite.
