# Détail Exclusive Offer (Flutter) — polish i18n

## Nettoyé dans ce lot

- Chaînes visibles de l’écran détail EO branchées sur `AppLocalizations` (CTA, modales investissement, Documents / Galerie, liste vidéos promo, FAQ / erreurs chargement, libellés étapes milestone, compteur d’étapes Vault, titre FAQ par défaut, ligne investisseurs du bloc funding).
- Format APR du `FundingModule` (auto) : `NumberFormat.decimalPatternDigits` selon la locale système (`exclusive_offer_formatting.dart`), au lieu de `toStringAsFixed` brut.
- Suppression de la rangée de **stats Figma mock** (`DsFigmaStatsGridRow`) sur ce détail — reliquat non aligné builder.

## Hors scope volontaire

- **Italien** : l’app ne déclare que `en` / `fr` dans `AppLocalizations.supportedLocales` — pas de `it` sans élargir les locales et les ARB.
- **Montants levés / cibles** dans le bloc funding : toujours issus du builder ou du formatage existant côté `OfferProject` (espaces fines) ; pas de refonte `NumberFormat` currency sur toute la ligne dans ce lot.
- **Autres écrans** (liste offres, flux invest, etc.).
- Textes **100 % pilotés par le CMS** (modules vault, layout JSON) : inchangés.

## Lots futurs possibles

- Ajouter `it` (ou autres langues) aux ARB + `supportedLocales`.
- Unifier le format des grands nombres (montants) avec `intl` sur les chaînes catalogue si besoin produit.
