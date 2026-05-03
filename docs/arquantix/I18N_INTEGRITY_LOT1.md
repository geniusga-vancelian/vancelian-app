# Intégrité linguistique — Lot 1 (audit-only)

## Périmètre

- **Couche** : contenus `SectionContent` en statut **DRAFT** uniquement, pour la **locale cible** choisie (fr / en / it).
- **Vault Builder** (`template` vault + section `vault_builder_v1`) : chemins allowlistés dans le code (`auditVaultDraft.ts`) — modules `TitlePage`, `SimpleMarkdownContentModule`, `FaqAccordionModule`, plus champs racine `pageTitle.text`, `fixedBottomCta.label` si présents.
- **Sections CMS** : clés **`hero`**, **`hero_secondary`**, **`cta`** uniquement — champs allowlistés dans `auditCmsSectionDraft.ts` (pas de tags hero en lot 1).

## Ce que l’outil ne fait pas (encore)

- Aucune **traduction**, aucun **apply** sur brouillon ou publié.
- Aucune **écriture base de données**.
- Pas de scan **footer**, **menu**, **PageI18n**, **articles**, **help**, disclaimers.
- Pas de scan « tout le JSON » : uniquement les chemins explicitement listés.

## Statuts

| Statut | Sens (résumé) |
|--------|----------------|
| `OK` | Aligné avec la locale cible (détection suffisamment confiante). |
| `MISSING` | Champ vide ou absent. |
| `WRONG_LANGUAGE` | Langue détectée incompatible avec la cible. |
| `MIXED_LANGUAGE` | Mélange de langues dans le texte. |
| `NEEDS_REVIEW` | Texte trop court, ambigu, ou confiance insuffisante. |
| `NON_TRANSLATABLE` | Réservé ; peu utilisé en lot 1 (champs exclus plutôt que rapportés). |

## Point d’entrée

- **API** : `GET /api/admin/i18n/integrity/scan?targetLocale=en` (session admin requise).
- **UI** : `/admin/i18n/integrity` — lecture seule, affichage du rapport JSON.

## Garde-fous

- Détection basée sur **franc** + heuristiques (seuils, textes courts → `NEEDS_REVIEW`).
- Préparation du texte : URLs / patterns exclus, markdown allégé — voir `textPrep.ts` et `languageStatus.ts`.

## Lot 2 (prévu)

- Phase « prepare fixes » : propositions structurées sans apply automatique, puis apply ciblé sur brouillons uniquement — hors périmètre du lot 1.
