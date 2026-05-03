import type { Locale } from '@/config/locales'

/** Contenus de démo localisés (aperçu catalogue uniquement — pas écrit en base). */
type DemoLang = 'fr' | 'en'

function demoLang(locale: Locale): DemoLang {
  return locale === 'fr' ? 'fr' : 'en'
}

function shallowMerge(data: Record<string, unknown>, patch: Record<string, unknown>): void {
  for (const [k, v] of Object.entries(patch)) {
    if (v !== undefined) data[k] = v
  }
}

/**
 * Visuels Unsplash stables pour l’iframe « section-demo » (aperçu admin uniquement).
 * Permet de montrer le rôle réel des modules (image + texte, fond CTA, étapes illustrées…).
 */
const DEMO_VISUAL = {
  mediaText:
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=80',
  featureGridSide:
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80',
  /** Carte / illustration type planisphère — eau claire sur fond blanc (aperçu catalogue). */
  companyMapBg:
    'https://images.unsplash.com/photo-1587329310686-91414b8e3cb7?auto=format&fit=crop&w=2000&q=82',
  keyFiguresBg:
    'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80',
  ctaBg:
    'https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=2000&q=80',
  howStep1:
    'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=900&q=80',
  howStep2:
    'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
  howStep3:
    'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80',
  /** Avatars cartes Figma témoignages (aperçu catalogue) — 48×48 rendu, source 256px. */
  figmaTestimonialAvatar1:
    'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=256&q=80',
  figmaTestimonialAvatar2:
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=256&q=80',
} as const

const MEDIA_TEXT_COPY = {
  fr: {
    eyebrow: 'BLOC MÉDIA',
    title: 'Un visuel fort,\nun message clair',
    description:
      'Deux colonnes sur fond blanc : à gauche ou à droite selon l’option « image à droite » dans l’éditeur. La photo vient normalement de la médiathèque ; ici, une image d’exemple montre le rendu (coins arrondis, équilibre texte / image).',
    imageAlt: 'Intérieur contemporain — image de démonstration pour l’aperçu catalogue',
  },
  en: {
    eyebrow: 'MEDIA BLOCK',
    title: 'Strong visual,\nclear message',
    description:
      'Two columns on white: image left or right via the editor toggle. Production images come from the media library; this sample photo shows the layout (rounded corners, text balance).',
    imageAlt: 'Contemporary interior — demo preview image',
  },
} as const

const FAQ_COPY = {
  fr: {
    eyebrow: 'FAQ',
    title: 'Questions fréquentes',
    description:
      'Les réponses ci-dessous sont des exemples pour l’aperçu : après ajout du module, vous les remplacerez par vos vraies questions et réponses dans l’éditeur.',
    items: [
      {
        id: 'demo-faq-fr-1',
        question: 'Comment fonctionne ce module sur mon site ?',
        answerMarkdown:
          'Le bloc affiche une liste de **questions cliquables** ; chaque réponse se déploie sous la question. C’est idéal pour lever les freins avant une inscription ou un contact.',
      },
      {
        id: 'demo-faq-fr-2',
        question: 'Puis-je avoir autant de questions que je veux ?',
        answerMarkdown:
          'Oui. En édition, vous ajoutez ou supprimez des entrées. Sur mobile, l’accordéon reste lisible : une seule zone ouverte à la fois évite les pages interminables.',
      },
      {
        id: 'demo-faq-fr-3',
        question: 'Le texte des réponses supporte-t-il la mise en forme ?',
        answerMarkdown:
          'Les réponses sont en Markdown : paragraphes, **mise en emphase**, liens `[texte](url)`, etc. Évitez les réponses trop longues : mieux vaut plusieurs questions ciblées.',
      },
      {
        id: 'demo-faq-fr-4',
        question: 'Où modifier ce contenu après l’avoir ajouté à la page ?',
        answerMarkdown:
          'Depuis la liste des modules de la page, ouvrez **Modifier** sur la section FAQ (sauf modules communs, édités dans Structure du site). Les champs sont traduits par langue comme le reste du site.',
      },
    ],
  },
  en: {
    eyebrow: 'FAQ',
    title: 'Frequently asked questions',
    description:
      'The Q&A below is sample content for this preview. After you add the module, replace it with your real questions and answers in the editor.',
    items: [
      {
        id: 'demo-faq-en-1',
        question: 'How does this module behave on the live site?',
        answerMarkdown:
          'It renders a list of **clickable questions**; each answer expands underneath. It works well to remove doubts before signup or contact.',
      },
      {
        id: 'demo-faq-en-2',
        question: 'Can I add as many questions as I need?',
        answerMarkdown:
          'Yes. In the editor you add or remove rows. On small screens the accordion stays readable—typically one open item at a time.',
      },
      {
        id: 'demo-faq-en-3',
        question: 'Do answers support rich formatting?',
        answerMarkdown:
          'Answers use Markdown: paragraphs, **bold**, links `[label](url)`, and more. Prefer several short Q&As over one very long answer.',
      },
      {
        id: 'demo-faq-en-4',
        question: 'Where do I edit this after placing it on the page?',
        answerMarkdown:
          'From the page module list, open **Edit** on the FAQ section (common modules are edited under Site structure). Fields are localized like the rest of the site.',
      },
    ],
  },
} as const

const TESTIMONIALS_COPY = {
  fr: {
    eyebrow: 'TÉMOIGNAGES',
    title: 'Ils témoignent',
    description:
      'Trois cartes d’exemple (note sur 5 + citation + nom). Remplacez-les par de vrais retours clients dans l’éditeur.',
    items: [
      {
        name: 'Claire M.',
        title: 'Family office',
        text: 'Parcours clair, documentation accessible — nous avons gagné un temps précieux sur la phase de décision.',
        rating: 5,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=256&q=80',
      },
      {
        name: 'Thomas R.',
        title: 'Investisseur privé',
        text: 'La transparence sur les projets et le suivi nous rassure. L’équipe répond vite aux questions opérationnelles.',
        rating: 5,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=256&q=80',
      },
      {
        name: 'Sophie L.',
        title: 'CGP',
        text: 'Nous apprécions la cohérence du discours et des supports pour nos clients finaux.',
        rating: 4,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=256&q=80',
      },
    ],
  },
  en: {
    eyebrow: 'TESTIMONIALS',
    title: 'What clients say',
    description:
      'Three sample cards (5-star rating, quote, name). Swap them for real client feedback in the editor.',
    items: [
      {
        name: 'Claire M.',
        title: 'Family office',
        text: 'Clear process and solid documentation—we saved a lot of time in the decision phase.',
        rating: 5,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=256&q=80',
      },
      {
        name: 'Thomas R.',
        title: 'Private investor',
        text: 'Project transparency and follow-up are strong. The team is responsive on operational questions.',
        rating: 5,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=256&q=80',
      },
      {
        name: 'Sophie L.',
        title: 'Wealth advisor',
        text: 'Consistent narrative and materials we can reuse with end clients.',
        rating: 4,
        avatarMediaUrl:
          'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=256&q=80',
      },
    ],
  },
} as const

const HOW_IT_WORKS_COPY = {
  fr: {
    label: 'COMMENT ÇA MARCHE',
    title: 'Trois étapes pour investir',
    subtitle: 'Un parcours linéaire : comprendre, choisir, agir.',
    primaryCtaText: 'COMMENCER',
    steps: [
      {
        number: '01',
        title: 'Créer un compte',
        description:
          'Inscription guidée et vérification d’identité. Vous accédez ensuite au catalogue et aux documents réglementaires.',
        imageMediaUrl: DEMO_VISUAL.howStep1,
        imageMediaAlt: 'Équipe au travail — illustration étape 1 (démo)',
      },
      {
        number: '02',
        title: 'Explorer les opportunités',
        description:
          'Fiches projet, localisation, horizon, documentation : tout est centralisé pour comparer sereinement les offres.',
        imageMediaUrl: DEMO_VISUAL.howStep2,
        imageMediaAlt: 'Analyse et tableaux — illustration étape 2 (démo)',
      },
      {
        number: '03',
        title: 'Souscrire et suivre',
        description:
          'Une fois la décision prise, la souscription se fait en ligne. Vous suivez ensuite l’avancement depuis votre espace.',
        imageMediaUrl: DEMO_VISUAL.howStep3,
        imageMediaAlt: 'Signature et suivi — illustration étape 3 (démo)',
      },
    ],
  },
  en: {
    label: 'HOW IT WORKS',
    title: 'Three steps to get started',
    subtitle: 'A simple path: understand, compare, act.',
    primaryCtaText: 'START',
    steps: [
      {
        number: '01',
        title: 'Create your account',
        description:
          'Guided onboarding and identity checks. You then access the catalog and regulatory documents.',
        imageMediaUrl: DEMO_VISUAL.howStep1,
        imageMediaAlt: 'Team at work — step 1 demo illustration',
      },
      {
        number: '02',
        title: 'Explore opportunities',
        description:
          'Project sheets, location, horizon, docs—everything in one place to compare offers with confidence.',
        imageMediaUrl: DEMO_VISUAL.howStep2,
        imageMediaAlt: 'Analytics — step 2 demo illustration',
      },
      {
        number: '03',
        title: 'Subscribe and track',
        description:
          'Subscribe online when you are ready. Monitor progress from your investor area.',
        imageMediaUrl: DEMO_VISUAL.howStep3,
        imageMediaAlt: 'Signing — step 3 demo illustration',
      },
    ],
  },
} as const

const FIGMA_STATS_COPY = {
  fr: {
    eyebrow: 'CHIFFRES',
    title: 'Quelques repères',
    description: 'Grille type « stats » : grandes valeurs + libellés courts. À adapter à vos propres indicateurs.',
    stats: [
      { value: '12+', label: 'Années d’expérience' },
      { value: '40+', label: 'Projets financés' },
      { value: '8', label: 'Pays couverts' },
    ],
  },
  en: {
    eyebrow: 'STATS',
    title: 'Key figures at a glance',
    description: 'Figma-style stat grid: bold values and short labels. Replace with your own KPIs.',
    stats: [
      { value: '12+', label: 'Years of track record' },
      { value: '40+', label: 'Projects funded' },
      { value: '8', label: 'Countries' },
    ],
  },
} as const

const KEY_FIGURES_TITLE = {
  fr: 'Des repères pour décider',
  en: 'Figures that matter',
} as const

const FIGMA_TESTIMONIAL_CARDS_COPY = {
  fr: {
    eyebrow: 'AVIS',
    title: 'Témoignages (cartes Figma)',
    description:
      'Variante « cartes grises » distincte du module Témoignages à étoiles. Ici : auteur, rôle et texte dans une carte configurable.',
    items: [
      {
        author: 'Marie D.',
        role: 'Investisseuse',
        content:
          'Exemple de carte : citation plus longue, fond gris, auteur et rôle affichés comme sur la maquette Figma.',
        backgroundColor: '#f4f4f4',
        avatarMediaUrl: DEMO_VISUAL.figmaTestimonialAvatar1,
      },
      {
        author: 'Julien P.',
        role: 'Dirigeant PME',
        content:
          'Deuxième carte pour montrer la grille (1 ou 2 cartes par ligne selon le réglage dans l’éditeur).',
        backgroundColor: '#eeeeee',
        avatarMediaUrl: DEMO_VISUAL.figmaTestimonialAvatar2,
      },
    ],
  },
  en: {
    eyebrow: 'VOICES',
    title: 'Testimonial cards (Figma)',
    description:
      'Gray-card variant, separate from the star-rating Testimonials module. Author, role, and quote per card.',
    items: [
      {
        author: 'Marie D.',
        role: 'Investor',
        content:
          'Sample card: longer quote, gray background, author and role as in the Figma handoff.',
        backgroundColor: '#f4f4f4',
        avatarMediaUrl: DEMO_VISUAL.figmaTestimonialAvatar1,
      },
      {
        author: 'Julien P.',
        role: 'SME founder',
        content:
          'Second card to illustrate the grid (1 or 2 cards per row depending on editor settings).',
        backgroundColor: '#eeeeee',
        avatarMediaUrl: DEMO_VISUAL.figmaTestimonialAvatar2,
      },
    ],
  },
} as const

const FEATURE_GRID_COPY = {
  fr: {
    title: 'Pourquoi nous choisir',
    description: 'Trois arguments courts en grille — remplacez par vos propres promesses.',
    items: [
      {
        title: 'Expertise terrain',
        description: 'Une équipe qui suit les projets de la structuration au suivi post-financement.',
      },
      {
        title: 'Transparence',
        description: 'Documents et indicateurs clés accessibles avant toute décision.',
      },
      {
        title: 'Accompagnement',
        description: 'Un interlocuteur dédié pour sécuriser le parcours investisseur.',
      },
    ],
  },
  en: {
    title: 'Why work with us',
    description: 'Three short value props—swap for your own messaging.',
    items: [
      {
        title: 'On-the-ground expertise',
        description: 'We stay close to projects from structuring through post-funding monitoring.',
      },
      {
        title: 'Transparency',
        description: 'Key documents and metrics available before you commit.',
      },
      {
        title: 'Support',
        description: 'A dedicated contact to keep the investor journey smooth.',
      },
    ],
  },
} as const

const HERO_DEMO_COPY = {
  fr: {
    title: 'Investir dans le\nréel, simplement',
    subtitle: 'Un aperçu du hero pleine largeur : titre sur deux lignes, sous-titre et bouton d’action.',
    ctaText: 'Découvrir les projets',
    ctaLink: '#',
  },
  en: {
    title: 'Premium real assets,\nstraightforward access',
    subtitle: 'Preview of the full-width hero: two-line title, subtitle, and primary CTA.',
    ctaText: 'Explore projects',
    ctaLink: '#',
  },
} as const

/** Photos d’architecture / ville — démo uniquement (aperçu catalogue), tirage aléatoire à chaque rendu serveur. */
const HERO_SECONDARY_DEMO_BACKGROUNDS = [
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1460472178825-e5240623afd5?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=2000&q=80',
  'https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?auto=format&fit=crop&w=2000&q=80',
] as const

function pickRandomHeroSecondaryDemoBackground(): string {
  const i = Math.floor(Math.random() * HERO_SECONDARY_DEMO_BACKGROUNDS.length)
  return HERO_SECONDARY_DEMO_BACKGROUNDS[i]!
}

const BLOG_ARTICLE_HERO_DEMO = {
  fr: {
    title: 'Titre du hero (aperçu catalogue)',
    standfirst:
      'Chapô entièrement CMS — même grille que l’en-tête d’un article, sans contenu Prisma. Remplacez ces textes après ajout du module.',
    categoryPillLabels: ['Analyse', 'Marchés'],
    editorialPillLabel: '',
    authorName: 'Camille Dupont',
    authorRole: 'Rédaction',
    readingTimeText: '5 min de lecture',
    publishedAtIso: '2024-09-12T08:00:00.000Z',
    updatedAtIso: '2024-10-01T14:30:00.000Z',
    coverTitle: 'Visuel de couverture',
    coverCredit: 'Photo',
    coverSource: 'Unsplash (démo)',
  },
  en: {
    title: 'Hero headline (catalog preview)',
    standfirst:
      'Fully CMS standfirst — same grid as an article header, no Prisma body. Replace this copy after adding the module.',
    categoryPillLabels: ['Analysis', 'Markets'],
    editorialPillLabel: '',
    authorName: 'Jane Doe',
    authorRole: 'Editorial',
    readingTimeText: '5 min read',
    publishedAtIso: '2024-09-12T08:00:00.000Z',
    updatedAtIso: '2024-10-01T14:30:00.000Z',
    coverTitle: 'Cover visual',
    coverCredit: 'Photo',
    coverSource: 'Unsplash (demo)',
  },
} as const

const HERO_SECONDARY_DEMO_COPY = {
  fr: {
    title: 'Titre de page,\ndeuxième ligne',
    subtitle:
      'Grand bandeau du haut de page (hors accueil) — le hero principal de cette page. Texte en contraste sur photo ; image Unsplash tirée au sort à chaque chargement de l’aperçu (démo).',
    ctaText: 'Découvrir',
    ctaLink: '#',
  },
  en: {
    title: 'Page headline,\nsecond line',
    subtitle:
      'Main hero at the top of non-home pages—this page’s primary hero. Light text over a photo; random Unsplash image on each preview load (demo only).',
    ctaText: 'Discover',
    ctaLink: '#',
  },
} as const

function isEmptyItems(x: unknown): boolean {
  return !Array.isArray(x) || x.length === 0
}

function stringIsBlank(s: unknown): boolean {
  return typeof s !== 'string' || s.trim() === ''
}

/**
 * Remplace / complète les `defaultData` du catalogue pour l’iframe « section-demo » (admin).
 * Ne modifie pas les defaults en base ni dans `library.ts`.
 */
export function applySectionDemoEnrichment(
  effectiveKey: string,
  data: Record<string, unknown>,
  locale: Locale,
): void {
  const L = demoLang(locale)

  switch (effectiveKey) {
    case 'faq': {
      const block = FAQ_COPY[L]
      shallowMerge(data, {
        eyebrow: block.eyebrow,
        title: block.title,
        description: block.description,
        subtitle: '',
        items: block.items,
      })
      break
    }
    case 'testimonials': {
      if (!isEmptyItems(data.items)) break
      const block = TESTIMONIALS_COPY[L]
      shallowMerge(data, {
        eyebrow: block.eyebrow,
        title: block.title,
        description: block.description,
        items: block.items,
      })
      break
    }
    case 'how_it_works': {
      const block = HOW_IT_WORKS_COPY[L]
      shallowMerge(data, {
        label: block.label,
        title: block.title,
        subtitle: block.subtitle,
        primaryCtaText: block.primaryCtaText,
        steps: block.steps,
      })
      break
    }
    case 'figma_stats_grid': {
      const emptyHeader =
        stringIsBlank(data.eyebrow) && stringIsBlank(data.title) && stringIsBlank(data.description)
      if (!emptyHeader) break
      const block = FIGMA_STATS_COPY[L]
      shallowMerge(data, {
        eyebrow: block.eyebrow,
        title: block.title,
        description: block.description,
        stats: block.stats,
      })
      break
    }
    case 'key_figures': {
      delete data.backgroundMediaId
      const kfPatch: Record<string, unknown> = {
        backgroundMediaUrl: DEMO_VISUAL.keyFiguresBg,
        backgroundMediaAlt: L === 'fr' ? 'Gratte-ciels — fond démo' : 'Skyline — demo background',
      }
      if (stringIsBlank(data.title)) kfPatch.title = KEY_FIGURES_TITLE[L]
      shallowMerge(data, kfPatch)
      break
    }
    case 'figma_testimonial_cards': {
      const emptyHeader =
        stringIsBlank(data.eyebrow) && stringIsBlank(data.title) && stringIsBlank(data.description)
      if (!emptyHeader) break
      const block = FIGMA_TESTIMONIAL_CARDS_COPY[L]
      shallowMerge(data, {
        eyebrow: block.eyebrow,
        title: block.title,
        description: block.description,
        items: block.items,
      })
      break
    }
    case 'feature_grid': {
      delete data.imageMediaId
      const block = FEATURE_GRID_COPY[L]
      shallowMerge(data, {
        title: block.title,
        description: block.description,
        items: block.items,
        imageMediaUrl: DEMO_VISUAL.featureGridSide,
      })
      break
    }
    case 'media_text': {
      delete data.imageMediaId
      const m = MEDIA_TEXT_COPY[L]
      shallowMerge(data, {
        eyebrow: m.eyebrow,
        title: m.title,
        description: m.description,
        mediaRight: false,
        imageMediaUrl: DEMO_VISUAL.mediaText,
        imageMediaAlt: m.imageAlt,
      })
      break
    }
    case 'company_map': {
      delete data.backgroundMediaId
      shallowMerge(data, {
        backgroundMediaUrl: DEMO_VISUAL.companyMapBg,
        backgroundMediaAlt:
          L === 'fr'
            ? 'Carte monde — masses d’eau claires sur fond blanc (démo)'
            : 'World map — light water on white background (demo)',
      })
      break
    }
    case 'cta': {
      delete data.backgroundMediaId
      shallowMerge(data, {
        eyebrow: L === 'fr' ? 'Étape suivante' : 'Next step',
        backgroundMediaUrl: DEMO_VISUAL.ctaBg,
      })
      break
    }
    case 'hero': {
      const block = HERO_DEMO_COPY[L]
      shallowMerge(data, {
        title: block.title,
        subtitle: block.subtitle,
        ctaText: block.ctaText,
        ctaLink: block.ctaLink,
      })
      break
    }
    case 'hero_secondary': {
      const block = HERO_SECONDARY_DEMO_COPY[L]
      delete data.backgroundMediaId
      shallowMerge(data, {
        title: block.title,
        subtitle: block.subtitle,
        ctaText: block.ctaText,
        ctaLink: block.ctaLink,
        backgroundMediaUrl: pickRandomHeroSecondaryDemoBackground(),
        tags: L === 'fr' ? ['Immobilier', 'Institutionnel'] : ['Real estate', 'Institutional'],
      })
      break
    }
    case 'blog_article_hero': {
      delete data.imageMediaId
      const block = BLOG_ARTICLE_HERO_DEMO[L]
      shallowMerge(data, {
        title: block.title,
        standfirst: block.standfirst,
        categoryPillLabels: block.categoryPillLabels,
        editorialPillLabel: block.editorialPillLabel,
        authorName: block.authorName,
        authorRole: block.authorRole,
        readingTimeText: block.readingTimeText,
        publishedAtIso: block.publishedAtIso,
        updatedAtIso: block.updatedAtIso,
        coverTitle: block.coverTitle,
        coverCredit: block.coverCredit,
        coverSource: block.coverSource,
        imageMediaUrl: DEMO_VISUAL.mediaText,
      })
      break
    }
    default:
      break
  }
}
