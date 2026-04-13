# Rapport — création projet « Exclusive Offer » (import brochure)

## Synthèse

Une structure **canonique** pour une nouvelle offre exclusive a été ajoutée au dépôt : données TypeScript réutilisables, script Prisma **idempotent**, et entrée de projet **`PUBLISHED`** sous le slug `exclusive-offer-import`.

**Brochures PDF.** Aucune brochure produit n’a été trouvée dans le dépôt. Le seul PDF présent est `services/arquantix/docs/extract-qa-session.pdf` (FAQ technique admin / Flutter / Prisma), **sans contenu produit exploitable**. Les champs chiffrés et juridiques précis n’ont donc **pas** été renseignés (conformément à la consigne : ne pas inventer de données financières).

---

## 1. Mapping brochure → système

Ce tableau sert de référence lorsque les PDF seront disponibles. Il aligne le contenu papier / PDF avec le stockage et l’UI mobile.

| Contenu brochure (typique) | Stockage backend (Prisma) | Rendu UI mobile (Flutter) |
|----------------------------|---------------------------|---------------------------|
| Titre commercial, sous-titre | `projects` + `project_i18n.title`, `short_description` | Carte offre + en-tête détail (`OfferProject.title`, `shortDescription`) |
| Paragraphes de présentation, risques | `project_i18n.description` (Markdown) | Bloc description (`ExclusiveOfferDetailScreen`, markdown) |
| Liens (site émetteur, réglementation) | `project_i18n.description_links` `[{ label, url }]` | Liens sous la description |
| Schéma / étapes d’investissement | `project_i18n.how_it_works` `{ title, content, links[] }` | Module « comment ça marche » |
| Tableau objectif / durée / devise / ticket | `project_i18n.key_information` `{ title, rows[] }` | Table « informations clés » + modales `infoTitle` / `infoContent` |
| Piliers « pourquoi nous » | `project_i18n.competitive_advantages` `{ title, rows[{ icon, iconBackgroundColor, title, description }] }` | `CompetitiveAdvantagesModule` (icônes : `insights_rounded`, `assignment_turned_in_rounded`, `trending_up_rounded`, etc.) |
| FAQ / renvois aide | `project_i18n.faq` (articles Help Center par `articleId`, etc.) | Accordéon FAQ |
| Visuel couverture, hero, galerie | `projects.cover_media_id`, `hero_media_id`, `project_media` | `coverUrl`, carrousel galerie |
| Teaser vidéo | `projects.youtube_url` | Bouton lecture teaser |
| Catégorie (immobilier, énergie, etc.) | `projects.investment_category` | Tag catégorie (`normalizeInvestmentCategory` côté API) |
| **Données de collecte** (objectif, collecté, APY, statut, investissable) | **API Python** `lending_pool_products` lié par `project_id` | Jauge, métriques, flux invest (`GET /api/projects` enrichi) |

Les brochures **ne remplissent pas** directement `lending_pool_products` : après validation des montants et taux, création / liaison via l’API lending ou l’admin métier (voir `PROJECT_LENDING_INTEGRATION_PHASE2A11_REPORT.md`).

---

## 2. Fichiers créés ou modifiés

| Fichier | Rôle |
|---------|------|
| `services/arquantix/web/prisma/data/exclusive-offer-project-template.ts` | **Source de vérité** éditoriale : textes FR, JSON modules (howItWorks, keyInformation, competitiveAdvantages, faq). |
| `services/arquantix/web/scripts/seed-exclusive-offer-project.ts` | Upsert `projects` + `project_i18n` pour le slug `exclusive-offer-import`. |
| `services/arquantix/web/package.json` | Script npm `db:seed:exclusive-offer`. |
| `services/arquantix/EXCLUSIVE_OFFER_PROJECT_CREATION_REPORT.md` | Ce rapport. |

Aucun fichier existant du cœur métier (API Python, middleware, écrans Flutter) n’a été modifié.

---

## 3. Données insérées (aperçu)

- **Slug :** `exclusive-offer-import`
- **Statut :** `PUBLISHED` (visible dans `GET /api/projects` une fois la base à jour)
- **Locale :** `fr` (locale par défaut du produit)
- **Catégorie d’investissement :** `Private equity` (placeholder cohérent avec une offre privée ; à ajuster si la brochure indique « Infrastructure », « Real estate », etc.)
- **Modules remplis :** description (Markdown avec avertissements), how it works (3 étapes), key information (6 lignes dont nature de l’opération et document d’information), competitive advantages (3 cartes avec icônes supportées par le DS mobile)
- **Non renseigné volontairement :** `youtube_url`, `description_links`, liens how-it-works, entrées FAQ (tableau vide), **aucun** `cover_media_id` / `hero_media_id` / galerie

---

## 4. Champs manquants ou à compléter après réception des PDF

| Domaine | Détail |
|---------|--------|
| **Financier** | Rendement cible, coupon, ticket min/max, devise, montant cible, calendrier, frais : **non saisis** (valeurs textuelles « Non communiqué dans le dossier transmis au dépôt »). |
| **Juridique** | Forme exacte de l’opération, juridiction, document réglementaire : mentions génériques uniquement. |
| **Médias** | Aucune image : cover / hero / galerie à uploader (Media Library + association projet dans l’admin). |
| **Lending** | Aucun `lending_pool_product` ni lien `project_id` : pas de barre de progression ni APY dans l’app tant que la couche lending n’est pas créée et liée. |
| **FAQ** | Aucun article Help Center référencé : ajouter des `articleId` valides quand le contenu support existe. |

---

## 5. Points à relire manuellement

1. **Déposer les brochures PDF** dans le dépôt (ex. `services/arquantix/docs/brochures/`) ou les transmettre à l’équipe, puis mettre à jour `exclusive-offer-project-template.ts` ou l’admin.
2. **Revoir le slug** `exclusive-offer-import` avant mise en production (URL stable, SEO).
3. **Ajuster `investment_category`** pour correspondre aux libellés reconnus par l’API (`Real estate`, `Energy`, `Commodity`, `Art`, `Infrastructure`, `Private equity`, `Crypto`).
4. **Conformité / marketing** : valider le ton, les risques et les mentions réglementaires avec les équipes légales et conformité.
5. **Couverture média** : sans cover, la carte peut afficher un visuel vide ou un fallback selon l’implémentation ; prévoir au moins une image cover.
6. **Lien lending** : après fixation des paramètres réels, créer le produit côté API et associer `project_id` (voir endpoints dans `api/services/lending/offer_router.py`).

---

## 6. Vérification frontend (listing et détail)

- **API liste :** `GET /api/projects?locale=fr&limit=50` — le projet doit apparaître avec `slug` `exclusive-offer-import` et les champs JSON exposés.
- **Admin CMS :** édition sous la section projets (routes `/api/admin/projects` / écran admin projets selon votre build).
- **Flutter :** écran liste des offres puis `ExclusiveOfferDetailScreen` pour le même `id` ; modules `competitiveAdvantages`, `howItWorks`, `keyInformation` doivent se rendre sans erreur (icônes reconnues par `CompetitiveAdvantagesModule.iconFromKey`).

Commande d’amorçage locale (depuis `services/arquantix/web`, avec `DATABASE_URL` valide) :

```bash
npm run db:seed:exclusive-offer
```

---

## 7. Pistes pour la prochaine itération

- Dupliquer `getExclusiveOfferProjectTemplate()` vers un second export une fois les PDF intégrés, ou **éditer** le template et relancer le script (upsert idempotent).
- Optionnel : ajouter un script qui lit un PDF via `pypdf` et produit un **brouillon JSON** à valider manuellement avant injection (les PDF marketing ne sont pas toujours extractibles proprement).

---

*Document généré dans le cadre de la mission « nouveau projet Exclusive Offer » — avril 2026.*
