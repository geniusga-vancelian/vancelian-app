# Design System Arquantix (mobile)

Référence des tokens et composants pour garder une UI cohérente et maintenable.

## Règles d’usage

- **Ne pas** utiliser de couleurs ou polices en dur (`Colors.grey`, `Color(0x...)`, `fontSize: 14`) en dehors du DS.
- **Toujours** passer par `AppColors`, `AppTypography`, `AppSpacing`, `AppRadius` et les composants exportés par `design_system.dart`.
- Une seule police : **Inter** (titres, corps, labels). Pas de mélange avec d’autres familles sauf monospace pour le code.

---

## Couleurs (`AppColors`)

| Token | Usage |
|-------|--------|
| `textPrimary` | Texte principal, titres |
| `textSecondary` | Légendes, meta, description secondaire |
| `accent` | Liens, boutons primaires, éléments d’accent |
| `cardBackground` | Fond des cartes / écrans type chat |
| `pageBackground` | Fond de page (gris clair) |
| `border` | Bordures, séparateurs, tableaux Markdown |
| `navBarActivePill` | Fond pill actif, chips de suggestion, blockquote/code |
| `navBarInactive` | Icônes et texte inactifs (nav) |
| `userMessageBubble` | Fond bulle message utilisateur (chat) |
| `chatInputBg` / `chatInputHint` | Fond et placeholder de l’input chat |
| `errorBackground` / `errorText` | Bandeau et texte d’erreur |

---

## Typographie (`AppTypography`)

- **Titres** : `appBarTitle` (18), `welcomeTitle` (22), `sectionTitle`, `pageTitle`, `display*` / `headline*` / `title*`.
- **Corps** : `paragraph`, `paragraphSmall`, `paragraphLarge` — corps standard.
- **Chat** : `chatBody` (15, line height 1.55) pour bulles, Markdown et input chat.
- **Labels** : `label`, `labelMedium`, `labelSmall`, `labelLarge`, `inputLabel`, `meta`.
- **Montants** : `amountLarge`, `amountMedium`, `amountSmall`.

Éviter les `copyWith(fontSize: ...)` sauf cas très local ; privilégier un nouveau token dans le DS si le besoin revient.

---

## Espacement (`AppSpacing`)

`xs` (4), `sm` (8), `md` (12), `lg` (16), `xl` (20), `xxl` (24). Utiliser ces valeurs plutôt que des nombres en dur.

---

## Rayons (`AppRadius`)

`card` (12), `image` (10), `button` / `chip` (20), `navBarPill` (24), `sm` (8), `bubble` (18 pour bulles de message).

---

## Composants

- **AppSuggestionChip** : tag de suggestion (ex. catégories Search), un style unique.
- **AppFilterChip** : filtre / onglet (état sélectionné vs non sélectionné).
- **ChatInput** : champ de saisie chat (style chatBody, `navBarPill`).
- **AppPageTitle**, **AppSectionTitle** : titres de page et de section.
- Cartes : **CategoryCard**, **MarketingCard**, **ExclusiveOfferCard**, etc.
- **MarketingCardsCarousel** : carousel horizontal de cartes marketing (titre + liste).
- **MarketingCardsSlidingModule** : module cartes marketing avec sliding (PageView) et indicateurs en points sous les cartes ; réutilise `MarketingCardsCarouselItem` et `MarketingCard`.

---

## Fichiers principaux

- `atoms/app_colors.dart` — couleurs
- `atoms/app_typography.dart` — styles de texte (délègue à `typography.dart`)
- `atoms/app_spacing.dart` — espacements
- `atoms/app_radius.dart` — rayons
- `typography.dart` — définition des styles (Inter, tailles, line height)
- `components/` — composants réutilisables
