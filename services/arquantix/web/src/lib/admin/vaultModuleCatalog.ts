/**
 * Catalogue des modules Vault (landing) — source unique pour labels, defaults,
 * catégories (modal d’ajout) et résumés d’affichage (liste repliable).
 */

export type VaultModuleDefinition = {
  type: string
  label: string
  category: string
  hint?: string
  description?: string
  defaultContent: Record<string, unknown>
}

export const VAULT_MODULE_DEFINITIONS: VaultModuleDefinition[] = [
  {
    type: 'TitlePage',
    label: 'Title page module',
    category: 'En-tête & hero',
    hint: 'Titre, sous-titre, vidéos promo',
    description:
      'Bloc hero principal du vault : titre de section, sous-titre et médias promo (vidéo URL ou médiathèque selon la config produit).',
    defaultContent: {
      title: 'Titre de section',
      subtitle: '',
      promoVideoUrl: '',
      promoVideoUrls: [],
    },
  },
  {
    type: 'TagsModule',
    label: 'Tags (puces hero DS)',
    category: 'En-tête & hero',
    hint: 'Puces au-dessus du titre',
    description: 'Liste courte de tags affichés comme puces (design system) sous le hero.',
    defaultContent: { tags: ['Japan', '2 chalets'] },
  },
  {
    type: 'FundingModule',
    label: 'Funding (métriques)',
    category: 'Données & métriques',
    hint: 'Progression, APR, cible',
    description:
      'Barres / métriques de financement : progression, taux affiché, montant cible — mode auto lié produit ou saisie manuelle.',
    defaultContent: {
      title: '',
      displayMode: 'auto_product',
      footnote: '',
      items: [
        { key: 'progress', label: '', enabled: true },
        { key: 'apr', label: '', enabled: true },
        { key: 'target', label: '', enabled: true },
      ],
      manual: { progressPct: 0, rateDisplay: '', totalDisplay: '' },
    },
  },
  {
    type: 'SimpleMarkdownContentModule',
    label: 'Contenu simple Markdown + liens',
    category: 'Contenu & texte',
    hint: 'Texte riche',
    description:
      'Corps de texte en Markdown avec liens sortants — idéal pour l’argumentaire ou les paragraphes longs.',
    defaultContent: {
      moduleTitle: 'À propos',
      markdown:
        'Utilisez ce bloc pour afficher du contenu **Markdown** avec paragraphes, listes et mise en forme.',
      links: [{ label: 'En savoir plus', url: 'https://arquantix.com' }],
    },
  },
  {
    type: 'CompetitiveAdvantagesModule',
    label: 'Competitive Advantages Module',
    category: 'Marketing & listes',
    hint: 'Grille avantages',
    description:
      'Lignes avec icône, titre et description pour mettre en avant les atouts (couleurs de catégorie configurables).',
    defaultContent: {
      title: 'Pourquoi cette offre ?',
      rows: [
        {
          icon: 'assignment_turned_in_rounded',
          iconBackgroundColor: '#1E88E5',
          category: 'content',
          title: 'Process rigoureux',
          description: 'Une sélection stricte des opportunités avec gouvernance claire.',
        },
        {
          icon: 'insights_rounded',
          iconBackgroundColor: '#16A34A',
          category: 'success',
          title: 'Suivi data',
          description: 'Des indicateurs lisibles pour piloter la performance.',
        },
      ],
    },
  },
  {
    type: 'FaqAccordionModule',
    label: 'FAQ Accordion Module',
    category: 'Contenu & texte',
    hint: 'FAQ liées Help / Academy',
    description:
      'Accordéon de questions/réponses branché sur des articles Help via slugs ou collection.',
    defaultContent: {
      title: 'FAQ',
      intro: '',
      footerLinkLabel: 'Voir les FAQ du projet',
      footerCollectionSlug: 'getting-started',
      footerCategorySlug: 'investing-basics',
      footerFilterLabel: '',
      items: [{ articleSlug: 'what-is-investing' }],
    },
  },
  {
    type: 'ContentBasDePageSansModuleBlanc',
    label: 'content bas de page sans module blanc',
    category: 'Contenu & texte',
    hint: 'Mentions légales compactes',
    description: 'Bloc Markdown discret en bas de page (ex. CGU, mentions) sans fond carte blanche.',
    defaultContent: {
      markdown:
        "En participant à ce programme, vous confirmez avoir lu et accepté nos [conditions générales](https://arquantix.com).",
    },
  },
  {
    type: 'MarktingCardLargePortrait',
    label: 'MarktingCardLargePortrait',
    category: 'Marketing & listes',
    hint: 'Grande carte portrait',
    description: 'Carte marketing portrait pleine hauteur (asset ou image).',
    defaultContent: {
      title: 'Fluidifiez vos processus de travail',
      imageAssetPath: 'assets/marketing_card_large_portrait.png',
      heightSize: 'large',
    },
  },
  {
    type: 'MarketingCardsSmallCarouselModule',
    label: 'Marketing Cards Small Carousel',
    category: 'Marketing & listes',
    hint: 'Carrousel cartes',
    description: 'Carrousel de petites cartes marketing.',
    defaultContent: { items: [] },
  },
  {
    type: 'MarketingCardsSmallSlidingCarrousel_Portrait',
    label: 'Marketing Cards Small Sliding Carrousel (Portrait)',
    category: 'Marketing & listes',
    hint: 'Cartes portrait',
    description:
      'Carrousel coulissant avec cartes portrait — ratio et nombre de cartes visibles configurables.',
    defaultContent: {
      title: '',
      carousel: false,
      showBullets: true,
      visibleCardsCount: 1.2,
      cardAspectRatio: '1.2:1',
      items: [
        {
          imageUrl: 'https://picsum.photos/600/800',
          redirectUrl: 'https://arquantix.com',
          title: 'Carte portrait',
          description: '',
        },
      ],
    },
  },
  {
    type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
    label: 'Marketing Cards Small Sliding Carrousel (Paysage)',
    category: 'Marketing & listes',
    hint: 'Cartes paysage',
    description: 'Carrousel coulissant avec cartes au format paysage.',
    defaultContent: {
      title: '',
      carousel: false,
      showBullets: true,
      items: [
        {
          imageUrl: 'https://picsum.photos/800/600',
          redirectUrl: 'https://arquantix.com',
          title: 'Carte paysage',
          description: '',
        },
      ],
    },
  },
  {
    type: 'TransactionLatest10Module',
    label: 'Transaction Latest 10 Module',
    category: 'Données & métriques',
    hint: 'Dernières transactions',
    description: 'Liste des dernières transactions (limite configurable, ex. 10).',
    defaultContent: { title: 'Dernières transactions', limit: 10 },
  },
  {
    type: 'BlogALaUne',
    label: 'Blog A la Une',
    category: 'Marketing & listes',
    hint: 'Articles à la une',
    description: 'Sélection d’articles blog mis en avant sur la page vault.',
    defaultContent: { title: 'À la une', limit: 3 },
  },
  {
    type: 'AllocationModule',
    label: 'Allocation (Donuts)',
    category: 'Données & métriques',
    hint: 'Répartition en anneau',
    description: 'Graphique d’allocation type donut avec parts colorées et libellés.',
    defaultContent: {
      title: 'Allocation',
      introText: 'Votre portefeuille génère des intérêts grâce à une allocation dynamique.',
      size: 'large',
      slices: [
        { label: 'Energy', percentage: 38.2, colorHex: '#374151' },
        { label: 'Real estate', percentage: 28.5, colorHex: '#6B7280' },
        { label: 'Crypto', percentage: 15.0, colorHex: '#9CA3AF' },
        { label: 'Stablecoins', percentage: 10.3, colorHex: '#D1D5DB' },
        { label: 'Equity', percentage: 5.7, colorHex: '#E5E7EB' },
        { label: 'Others', percentage: 2.3, colorHex: '#CBD5E1' },
      ],
    },
  },
  {
    type: 'KeyInformationModule',
    label: 'Key Information',
    category: 'Données & métriques',
    hint: 'Tableau clé/valeur',
    description:
      'Tableau synthétique label / valeur (comme sur l’app), avec CTA optionnel et icônes info.',
    defaultContent: {
      title: 'Informations clés',
      ctaLabel: '',
      ctaHref: '',
      rows: [
        {
          label: "Type d'investissement",
          value: 'Co-financement en actif numérique',
          showInfoIcon: false,
          infoLinkArticle: '',
        },
        {
          label: 'Rendement annuel fixe',
          value: '10,7% à 11,5 % APR',
          showInfoIcon: false,
          infoLinkArticle: '',
        },
        {
          label: 'Paiement des intérêts',
          value: 'Quotidien',
          showInfoIcon: false,
          infoLinkArticle: '',
        },
        {
          label: "Période d'engagement",
          value: '18 mois',
          showInfoIcon: false,
          infoLinkArticle: '',
        },
        {
          label: 'Montant de souscription',
          value: "Pas de ticket d'entrée minimum",
          showInfoIcon: false,
          infoLinkArticle: '',
        },
        {
          label: 'Date de livraison',
          value: '2025',
          showInfoIcon: false,
          infoLinkArticle: '',
        },
      ],
    },
  },
  {
    type: 'MediaImageCarouselModule',
    label: 'Carrousel d’images (médiathèque)',
    category: 'Médias',
    hint: 'Galerie',
    description: 'Carrousel d’images issu de la médiathèque avec titre et description de module.',
    defaultContent: { moduleTitle: '', description: '', imageMediaIds: [] },
  },
  {
    type: 'DocumentsListModule',
    label: 'Liste de documents (médiathèque)',
    category: 'Médias',
    hint: 'PDF multiples',
    description: 'Liste téléchargeable de documents (PDF) avec libellés personnalisés.',
    defaultContent: { moduleTitle: '', description: '', documentEntries: [] },
  },
  {
    type: 'PerformanceChart',
    label: 'Performance Chart (Bundle)',
    category: 'Données & métriques',
    hint: 'Courbe performance',
    description: 'Graphique de performance pour offres type bundle.',
    defaultContent: { title: 'Performance' },
  },
  {
    type: 'StepsModule',
    label: 'Étapes / timeline (Steps)',
    category: 'Données & métriques',
    hint: 'Timeline verticale',
    description: 'Suite d’étapes avec dates, titres et tags — calendrier de projet.',
    defaultContent: {
      title: 'Étapes du projet',
      rightLabel: '',
      subtitle: '',
      items: [
        {
          dayLabel: 'Étape 1',
          date: '1er trimestre 2026',
          title: 'Lancement',
          description: 'Description courte de cette étape.',
          tags: ['Lancement'],
        },
        {
          dayLabel: 'Étape 2',
          date: '2e trimestre 2026',
          title: 'Déploiement',
          description: 'Suite du calendrier.',
          tags: [],
        },
      ],
    },
  },
  {
    type: 'VideoBlockArticleModule',
    label: 'Vidéos (cartes poster + lecture)',
    category: 'Médias',
    hint: 'Player + posters',
    description: 'Grille de vidéos avec poster, titre et date (même patterns que les articles).',
    defaultContent: {
      title: 'Vidéos',
      items: [
        {
          title: 'Titre de la vidéo',
          videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
          date: '7 avril 2026',
        },
      ],
    },
  },
  {
    type: 'LocalisationModule',
    label: 'Localisation (titre + description + carte Google)',
    category: 'Médias',
    hint: 'Carte embed',
    description: 'Titre, texte descriptif et iframe Google Maps pour situer le projet.',
    defaultContent: {
      moduleTitle: 'Localisation',
      description: 'Retrouvez l’emplacement du projet sur la carte ci-dessous.',
      embedUrl: '',
    },
  },
  {
    type: 'VirtualVisualizationModule',
    label: 'Visite virtuelle (Virtual visualization)',
    category: 'Médias',
    hint: 'Viewer Koma, lien iframe',
    description:
      'Titre, description et URL du viewer de visite virtuelle — affichée en iframe pleine largeur sur la fiche.',
    defaultContent: {
      moduleTitle: 'Visite virtuelle',
      description: 'Parcourez le projet en immersion 360°.',
      visualizationUrl:
        'https://virtual.komavisualization.com/vrViewer/b1c04f2e-5dd7-41ef-be4e-988ee110a14c/',
    },
  },
]

/** Structure catégorisée (même principe que `BLOCK_CATALOG` articles). */
export const VAULT_MODULE_CATALOG: Array<{
  category: string
  items: Array<{
    type: string
    label: string
    hint?: string
    description?: string
  }>
}> = (() => {
  const byCat = new Map<string, VaultModuleDefinition[]>()
  for (const d of VAULT_MODULE_DEFINITIONS) {
    if (!byCat.has(d.category)) byCat.set(d.category, [])
    byCat.get(d.category)!.push(d)
  }
  return [...byCat.entries()].map(([category, items]) => ({
    category,
    items: items.map((it) => ({
      type: it.type,
      label: it.label,
      ...(it.hint ? { hint: it.hint } : {}),
      ...(it.description ? { description: it.description } : {}),
    })),
  }))
})()

export function getVaultModuleDefinition(type: string): VaultModuleDefinition | undefined {
  return VAULT_MODULE_DEFINITIONS.find((d) => d.type === type)
}

export function getVaultModuleLabel(type: string): string {
  return getVaultModuleDefinition(type)?.label ?? type
}

/** Contenu par défaut pour un type (clone profond). */
export function getVaultModuleDefaultContent(type: string): Record<string, unknown> {
  const def = getVaultModuleDefinition(type)
  if (!def) return {}
  return structuredClone(def.defaultContent) as Record<string, unknown>
}

function str(val: unknown): string {
  return typeof val === 'string' ? val.trim() : ''
}

/** Résumé compact pour la barre repliable (liste de modules). */
export function getVaultModuleSummary(module: {
  type: string
  content: Record<string, unknown>
}): string {
  const c = module.content ?? {}
  switch (module.type) {
    case 'TitlePage':
      return str(c.title) || 'Title page — sans titre'
    case 'TagsModule': {
      const tags = c.tags
      if (Array.isArray(tags) && tags.length) return tags.map(String).join(' · ')
      return 'Tags vides'
    }
    case 'SimpleMarkdownContentModule':
      return str(c.moduleTitle) || 'Contenu Markdown'
    case 'FundingModule':
      return str(c.title) || 'Funding'
    case 'FaqAccordionModule':
      return str(c.title) || 'FAQ'
    case 'CompetitiveAdvantagesModule':
      return str(c.title) || 'Avantages'
    case 'KeyInformationModule':
      return str(c.title) || 'Informations clés'
    case 'MediaImageCarouselModule':
      return str(c.moduleTitle) || 'Carrousel'
    case 'DocumentsListModule':
      return str(c.moduleTitle) || 'Documents'
    case 'VideoBlockArticleModule':
      return str(c.title) || 'Vidéos'
    case 'LocalisationModule':
      return str(c.moduleTitle) || 'Localisation'
    case 'VirtualVisualizationModule':
      return str(c.moduleTitle) || 'Visite virtuelle'
    case 'StepsModule':
      return str(c.title) || 'Étapes'
    default:
      return getVaultModuleLabel(module.type)
  }
}
