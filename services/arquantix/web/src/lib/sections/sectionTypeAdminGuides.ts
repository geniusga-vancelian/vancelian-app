/**
 * Textes d’aide pour l’écran « Choisir un module » (CMS admin).
 * Complètent la courte `description` du catalogue par un guide lisible pour les éditeurs.
 */
export const SECTION_ADMIN_GUIDES: Record<string, string> = {
  hero:
    'Réservé à la page d’accueil : grand bandeau avec titre, sous-titre, image ou vidéo de fond, bouton d’action. Premier élément visible — à utiliser pour la promesse principale du site.',
  hero_secondary:
    'Pour toutes les pages sauf l’accueil : même principe que le hero d’accueil (titre, sous-titre, image de fond, CTA, pastilles optionnelles). C’est le premier bloc de la page intérieure, pas un « deuxième » bandeau sous le hero de la home.',
  feature_grid:
    'Grille de cartes « fonctionnalités » ou arguments (titre + courte description par carte). Idéal pour présenter 3 à 6 points forts en colonnes.',
  how_it_works:
    'Parcours étape par étape (numéros masquables) : surtitre, titre, chapô, puis cartes titre + texte. Chaque étape peut avoir une image (médiathèque) et un bouton lien. Les CTA du bas enchaînent vers catalogue ou contact. Viser 3 à 5 étapes pour rester lisible sur mobile.',
  cta:
    'Bloc d’appel à l’action : surtitre, titre, texte riche (Markdown), un ou deux boutons, fond image ou couleur. Pour convertir : inscription, contact, découverte d’offre.',
  project_grid:
    'Grille de cartes reliée au catalogue d’offres (sélection automatique ou manuelle) : visuels, titres, liens vers les fiches.',
  blog_list:
    'Liste d’articles (aperçu du blog). Le rendu peut être encore simplifié selon le thème ; vérifiez le résultat sur la prévisualisation.',
  blog_hero:
    'Mise en avant du principal article de blog (à la une), en haut d’une page rubrique Blog ou similaire.',
  blog_category_nav:
    'Type historique déprécié — non proposé à l’ajout. Ne s’affiche plus sur la page liste blog (gabarit CMS). Filtrage par catégorie : URLs / paramètres de requête et modules mosaïque ou flux.',
  blog_mosaic:
    'Grille magazine de plusieurs articles mis en avant sur la page. Libellés « Précédent » / « Suivant » de la pagination : champs dédiés (traduisibles).',
  blog_feed:
    'Liste chronologique des articles (pagination ou « voir plus »).',
  blog_article_hero:
    'Bandeau visuel type page article (fond gris, titre, méta, image ou vidéo) entièrement saisi dans le CMS — sans lien avec un article Prisma. À utiliser sur une landing ou toute page composable quand vous voulez ce layout sans lecteur. Pour une vraie page article (corps, blocs, sommaire), gardez le module « Blog — article complet (lecture) » sur le gabarit article.',
  blog_article_reader:
    'Article de blog en une page : en-tête alimenté par l’article publié (Prisma), puis corps, sommaire, documents et partage. À placer en premier sur le gabarit « article ». Les champs du module règlent l’enveloppe (fil d’Ariane, libellés sommaire / documents / durée de lecture). Pour un bandeau article 100 % CMS sur une autre page, utilisez « Blog — en-tête type article (CMS) ».',
  share_sm:
    'Liens ou boutons vers les réseaux sociaux pour partager la page ou l’article. Souvent en colonne à côté du contenu sur le gabarit article.',
  blog_article_related:
    'Grille d’articles « à lire ensuite » sous un article (hors article courant).',
  exclusive_offer_vault:
    'Bloc spécifique aux pages offre exclusive / vault (contenu dynamique lié au produit). Réservé aux gabarits concernés.',
  faq:
    'Module accordéon : chaque ligne est une question (toujours visible) et une réponse dépliable. Idéal pour les objections fréquentes (frais, délais, risques, compte, fiscalité…) plutôt que pour du contenu très long : une question = un sujet précis. Les réponses acceptent le Markdown (gras, liens, listes). Les entrées sont alignées entre langues dans l’éditeur pour garder la même structure de Q&R partout.',
  testimonials:
    'Grille de cartes grises avec note sur 5, citation et nom (plus un rôle optionnel sous le nom). Sans photo, l’avatar peut rester vide ; avec la médiathèque (`avatarMediaId`), une vignette s’affiche. Variez la longueur des textes pour tester le rendu ; gardez des citations authentiques en production.',
  help_hero_v1:
    'Centre d’aide : bandeau d’accueil avec titre, introduction ou accès à la recherche.',
  help_search_v1:
    'Centre d’aide : champ de recherche (module historique).',
  help_collections_grid_v1:
    'Centre d’aide : grandes rubriques présentées en grille.',
  help_categories_grid_v1:
    'Centre d’aide : sous-rubriques (catégories) au sein d’une collection.',
  help_collection_body_v1:
    'Centre d’aide : corps de page d’une collection (intro + listes).',
  help_breadcrumbs_v1:
    'Centre d’aide : fil d’Ariane pour se repérer dans les rubriques.',
  help_search_results_v1:
    'Centre d’aide : liste des articles correspondant à une recherche.',
  help_article_reader_v1:
    'Centre d’aide : affichage d’un article (titre, contenu, métadonnées).',
  help_sidebar_toc_v1:
    'Centre d’aide : sommaire latéral pour un article long.',
  figma_simple_hero:
    'Titre et texte d’introduction sans grande image de fond (variante legacy). Préférez les modules Hero d’accueil ou de page intérieure.',
  figma_stats_grid:
    'Grille de chiffres ou indicateurs (grande valeur + courte légende). Colonnes 3, 4 ou 6 selon le nombre de cartes. Remplacez les valeurs d’exemple par vos indicateurs réels.',
  key_figures:
    'Variante legacy : statistiques sur fond sombre avec image optionnelle. Préférez « Grille de statistiques » pour les nouvelles pages.',
  figma_testimonial_cards:
    'Citations ou avis en cartes (auteur, rôle, texte, couleur de fond). Style magazine, distinct des témoignages avec notes. 1 ou 2 cartes par ligne selon le réglage.',
  media_text:
    'Deux colonnes : texte (surtitre, titre, description) et image depuis la médiathèque, image à gauche ou à droite. Argumentaire, reportage, mise en avant.',
  company_map:
    'Carte ou illustration en arrière-plan (texte par-dessus) : présence internationale, zones couvertes, etc. Le rendu éclaircit les océans sur fond de page blanc pour garder un côté « eau blanche / très claire ».',
  header:
    'Barre de navigation du site. En général gérée au niveau du menu global — à n’ajouter sur une page que si vous savez pourquoi vous dupliquez la nav.',
  footer:
    'Pied de page complet. Souvent fourni globalement ; l’ajout sur une page CMS est rare.',
  common_module_ref:
    'Réinsère sur cette page un bloc déjà créé dans Structure du site → modules communs. Le contenu et les traductions se modifient sur la fiche du module commun, pas ici.',
}

export function getSectionAdminGuide(key: string): string {
  return SECTION_ADMIN_GUIDES[key] ?? ''
}
