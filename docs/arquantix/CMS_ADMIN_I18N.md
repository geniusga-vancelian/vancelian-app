# CMS admin — état i18n (Lot 6)

## Règle de complétude (par page, par locale)

Signal principal : pour chaque **section** de la page, présence d’un `SectionContent` **PUBLISHED** pour la locale.

- **Complet** : toutes les sections ont un publié pour cette locale **et** un minimum SEO existe — entrée `PageI18n` avec titre ou description non vide ; pour **fr** on peut retomber sur `Page.title` / `Page.description` si `PageI18n` absent.
- **Partiel** : au moins une section publiée mais pas toutes, ou uniquement des **DRAFT**, ou tout publié mais SEO insuffisant.
- **Absent** : aucune section publiée (et pas de brouillon) pour cette locale.
- **Sans sections** : la page n’a aucune section (les trois locales affichent ce niveau).

Aucune analyse du JSON des sections : on évite les heuristiques fragiles sur le corps du contenu.

## Badges dans la structure

Sur chaque ligne de l’arbre : `FR`, `EN`, `IT` avec ✓ / ⚠ / ✗ / — et une infobulle répétant le libellé ci-dessus.

## Copie inter-locales

`POST /api/admin/pages/[slug]/copy-locale-content` : copie **PUBLISHED** (sinon **DRAFT**) de la locale source vers des **DRAFT** sur la cible, plus `PageI18n` si disponible (ou champs Page pour la locale source = défaut). **Pas de traduction** : texte identique, relecture éditoriale requise.

## Prévisualisation

Les URLs d’aperçu utilisent le préfixe de locale (`siteStructurePublicUrl`). Le sélecteur **Langue éditée** pilote aussi l’aperçu « en un clic » et les liens externes depuis l’arbre.
