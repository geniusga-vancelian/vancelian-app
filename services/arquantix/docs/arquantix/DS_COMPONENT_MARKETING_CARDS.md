# Composant DS Flutter : marketing_cards

Ce document décrit le composant unifié **marketing_cards** enregistré dans le chapitre "component DS flutter" pour la base de données de composants. Il permet de réutiliser le même bloc dans les pages en s’appuyant sur le schéma JSON.

## Table Prisma

- **Chapitre** : `DsComponentChapter` (ex. `slug: "component_ds_flutter"`, `name: "component DS flutter"`).
- **Composant** : `DsComponent` (ex. `slug: "marketing_cards"`, `name: "Marketing cards"`, `schemaJson`).

## Schéma JSON du composant `marketing_cards`

Structure attendue pour `schema_json` et pour consommer le composant en Flutter.

```json
{
  "title": "string | null",
  "layout": "portrait | landscape",
  "mode": "sliding | carousel",
  "items": [
    {
      "imageUrl": "string (required)",
      "redirectUrl": "string (required)",
      "title": "string | null",
      "description": "string | null",
      "logoLabel": "string | null",
      "buttonLabel": "string | null"
    }
  ]
}
```

### Paramètres du module

| Champ     | Type     | Obligatoire | Description |
|----------|----------|-------------|-------------|
| `title`  | string   | Non         | Titre affiché au-dessus des cartes. |
| `layout` | enum     | Oui         | `portrait` (ratio 1.2) ou `landscape` (ratio 0.75). |
| `mode`   | enum     | Oui         | `sliding` (une carte à la fois, sans bullets) ou `carousel` (défilement avec bullets). |
| `items`  | array    | Oui         | Liste des cartes (au moins une). |

### Paramètres par carte (`items[]`)

| Champ         | Type   | Obligatoire | Description |
|---------------|--------|-------------|-------------|
| `imageUrl`    | string | Oui         | URL de l’image de fond. |
| `redirectUrl` | string | Oui         | URL ouverte au clic sur la carte (redirection). |
| `title`       | string | Non         | Titre de la carte (une ligne recommandée). |
| `description` | string | Non         | Texte sous le titre (ex. 2 lignes). |
| `logoLabel`   | string | Non         | Lettre ou court texte dans le disque en haut à gauche (ex. "R"). |
| `buttonLabel` | string | Non         | Libellé du bouton (optionnel). |

## Exemple JSON complet

```json
{
  "title": "À la une",
  "layout": "landscape",
  "mode": "sliding",
  "items": [
    {
      "imageUrl": "https://picsum.photos/600/400?random=1",
      "redirectUrl": "https://example.com/offre-1",
      "title": "Revolut People",
      "description": "Gérez vos employés de A à Z sur une seule et même interface. Tout centralisé, tout simplifié.",
      "logoLabel": "R"
    },
    {
      "imageUrl": "https://picsum.photos/600/400?random=2",
      "redirectUrl": "https://example.com/offre-2",
      "title": "Équipes & productivité",
      "description": "Productivité et suivi en temps réel. Une seule interface pour toute l'équipe.",
      "logoLabel": "A"
    }
  ]
}
```

## Utilisation en Flutter

- **Widget** : `MarketingCardsModule` (design_system)
- **Config d’une carte** : `MarketingCardItemConfig`
- **Redirection** : fournir `onRedirect: (String url) => ...` (ex. `url_launcher`).

```dart
MarketingCardsModule(
  title: data['title'] as String?,
  layout: data['layout'] == 'portrait'
      ? MarketingCardsLayout.portrait
      : MarketingCardsLayout.landscape,
  mode: data['mode'] == 'carousel'
      ? MarketingCardsMode.carousel
      : MarketingCardsMode.sliding,
  items: (data['items'] as List)
      .map((e) => MarketingCardItemConfig(
            imageUrl: e['imageUrl'] as String,
            redirectUrl: e['redirectUrl'] as String,
            title: e['title'] as String?,
            description: e['description'] as String?,
            logoLabel: e['logoLabel'] as String?,
            buttonLabel: e['buttonLabel'] as String?,
          ))
      .toList(),
  onRedirect: (url) => launchUrl(Uri.parse(url)),
)
```

## Seed SQL (insert chapitre + composant)

À exécuter après la migration `20260303120000_add_ds_component_chapters` :

```sql
-- Chapitre "component DS flutter"
INSERT INTO ds_component_chapters (id, name, slug, "order", created_at)
VALUES ('c_ds_flutter_001', 'component DS flutter', 'component_ds_flutter', 0, NOW());

-- Composant marketing_cards (schema_json au format ci-dessus)
INSERT INTO ds_components (id, chapter_id, slug, name, schema_json, created_at)
VALUES (
  'comp_marketing_cards_001',
  'c_ds_flutter_001',
  'marketing_cards',
  'Marketing cards',
  '{
    "title": "À la une",
    "layout": "landscape",
    "mode": "sliding",
    "items": [
      {
        "imageUrl": "https://picsum.photos/600/400?random=1",
        "redirectUrl": "https://example.com/1",
        "title": "Revolut People",
        "description": "Gérez vos employés de A à Z. Tout centralisé, tout simplifié.",
        "logoLabel": "R"
      },
      {
        "imageUrl": "https://picsum.photos/600/400?random=2",
        "redirectUrl": "https://example.com/2",
        "title": "Équipes & productivité",
        "description": "Productivité et suivi en temps réel. Une seule interface.",
        "logoLabel": "A"
      }
    ]
  }'::jsonb,
  NOW()
);
```
