import { ArticleBlockType } from '@prisma/client'

/** Tous les types de blocs sélectionnables manuellement (le legacy `IMAGE` reste persisté pour les anciens blocs mais n'est plus exposé à la création). */
export type AddableBlockType = Exclude<ArticleBlockType, 'IMAGE'>

/**
 * Catalogue catégorisé pour le menu / la page « Ajouter un bloc » de l'admin
 * article. La même structure alimente le DropdownMenu legacy ET la nouvelle
 * page modale `/admin/articles/[id]/add-block` (pattern Page Builder).
 */
export const BLOCK_CATALOG: Array<{
  category: string
  items: Array<{ type: AddableBlockType; label: string; hint?: string; description?: string }>
}> = [
  {
    category: 'Texte',
    items: [
      {
        type: 'HEADING',
        label: 'Titre (Heading)',
        hint: 'Sous-titre ou intertitre',
        description:
          "Titre de niveau 2 ou 3 dans le corps de l'article. Affiché en grand, démarre une nouvelle section.",
      },
      {
        type: 'PARAGRAPH',
        label: 'Paragraphe',
        hint: 'Markdown supporté',
        description:
          'Bloc de texte courant. Markdown léger pris en charge (gras, italique, liens). Idéal pour le corps narratif.',
      },
      {
        type: 'QUOTE',
        label: 'Citation',
        hint: 'Avec attribution',
        description:
          'Citation mise en exergue avec attribution (auteur). Style typographique distinct du paragraphe.',
      },
      {
        type: 'BULLET_LIST',
        label: 'Liste à puces',
        description: "Liste verticale d'items à puces. Idéal pour énumérer des points clés.",
      },
      {
        type: 'NUMBERED_LIST',
        label: 'Liste numérotée',
        description: "Liste verticale d'items numérotés (1., 2., 3.). Pour des étapes ou des classements.",
      },
    ],
  },
  {
    category: 'Média',
    items: [
      {
        type: 'MEDIA_IMAGE_CAROUSEL',
        label: "Carrousel d'images",
        hint: 'Plusieurs images défilantes',
        description:
          "Carrousel horizontal d'images depuis la médiathèque, avec titre et description optionnels. Mieux pour des galeries de plusieurs visuels.",
      },
      {
        type: 'VIDEO',
        label: 'Vidéo (URL)',
        hint: 'YouTube ou Vimeo',
        description:
          "Insertion d'une seule vidéo via URL YouTube ou Vimeo, avec légende optionnelle. Bloc simple, pas de poster personnalisé.",
      },
      {
        type: 'VIDEO_BLOCK_ARTICLE',
        label: 'Vidéos avec posters',
        hint: 'Cartes lecture',
        description:
          'Bloc de cartes vidéos avec poster image personnalisé, titre et date par item. Utilisé pour des collections (interview, témoignage, démo).',
      },
      {
        type: 'DOCUMENT',
        label: 'Document (1 fichier)',
        hint: 'PDF unique',
        description:
          "Pièce jointe unique (PDF) téléchargeable depuis la médiathèque. Pour mettre en avant un seul document.",
      },
    ],
  },
  {
    category: 'Pratique',
    items: [
      {
        type: 'DOCUMENTS_LIST',
        label: 'Liste de documents',
        hint: 'Plusieurs PDF avec noms',
        description:
          'Liste de plusieurs documents PDF depuis la médiathèque, chacun avec un nom personnalisable. Idéal pour les annexes réglementaires.',
      },
      {
        type: 'KEY_INFORMATION',
        label: 'Informations clés',
        hint: 'Tableau label / valeur',
        description:
          'Tableau de paires label/valeur (ex. capital min, fréquence, durée), avec CTA optionnel. Utilisé pour résumer les caractéristiques d’une offre.',
      },
      {
        type: 'LOCALISATION',
        label: 'Localisation (carte)',
        hint: 'iframe Google Maps',
        description:
          'Bloc avec titre, description et embed Google Maps via iframe. Pour situer un événement, un bureau ou un projet immobilier.',
      },
    ],
  },
  {
    category: 'Parcours',
    items: [
      {
        type: 'STEPS_MODULE',
        label: 'Étapes (timeline)',
        hint: 'Verticales avec statut',
        description:
          'Timeline verticale d’étapes, chacune avec titre, date, description et statut (complété ou non). Pour visualiser un cycle de vie ou un calendrier.',
      },
      {
        type: 'HOW_IT_WORKS_CAROUSEL',
        label: 'Parcours étape par étape (carrousel)',
        hint: 'Cartes horizontales avec image',
        description:
          'Carrousel horizontal d’étapes (cards swipables avec numéro, titre, image optionnelle, CTA par étape). Idéal pour expliquer un processus en plusieurs phases sur une page sobre.',
      },
    ],
  },
]

export const BLOCK_TYPE_LABELS: Record<AddableBlockType, string> = (() => {
  const out: Partial<Record<AddableBlockType, string>> = {}
  for (const cat of BLOCK_CATALOG) {
    for (const it of cat.items) {
      out[it.type] = it.label
    }
  }
  return out as Record<AddableBlockType, string>
})()

/**
 * Données par défaut à la création d'un bloc (payload `data` côté API).
 * Identique à la définition historiquement présente dans
 * `handleAddBlock` du fichier `/admin/articles/[id]/page.tsx`.
 */
export function getDefaultBlockData(type: AddableBlockType): Record<string, unknown> {
  switch (type) {
    case 'HEADING':
      return { text: '' }
    case 'PARAGRAPH':
      return { text: '' }
    case 'QUOTE':
      return { text: '', author: '' }
    case 'BULLET_LIST':
      return { items: [''] }
    case 'NUMBERED_LIST':
      return { items: [''] }
    case 'VIDEO':
      return { url: '', caption: '' }
    case 'DOCUMENT':
      return { mediaId: '', title: '' }
    case 'MEDIA_IMAGE_CAROUSEL':
      return { moduleTitle: '', description: '', imageMediaIds: [] as string[] }
    case 'LOCALISATION':
      return { moduleTitle: 'Localisation', description: '', embedUrl: '' }
    case 'DOCUMENTS_LIST':
      return { subtitle: '', moduleTitle: '', description: '', documentEntries: [] as unknown[] }
    case 'KEY_INFORMATION':
      return {
        title: 'Informations clés',
        ctaLabel: '',
        ctaHref: '',
        rows: [{ label: '', value: '' }],
      }
    case 'VIDEO_BLOCK_ARTICLE':
      return { title: '', items: [] as unknown[] }
    case 'STEPS_MODULE':
      return {
        title: '',
        subtitle: '',
        description: '',
        rightLabel: '',
        items: [
          {
            dayLabel: '',
            date: 'Over',
            title: 'Période de souscription',
            description: '',
            isCompleted: true,
          },
          {
            dayLabel: '',
            date: 'Over',
            title: 'Clôture de la période de souscription',
            description: '',
            isCompleted: true,
          },
          {
            dayLabel: '',
            date: '',
            title: 'Versement des intérêts*',
            description:
              'Tous les mois après la date de clôture de la période de souscription.',
            isCompleted: false,
          },
        ] as unknown[],
      }
    case 'HOW_IT_WORKS_CAROUSEL':
      return {
        label: 'HOW IT WORKS',
        title: '',
        subtitle: '',
        hideStepNumbering: false,
        surface: 'light',
        steps: [
          { number: '01', title: '', description: '' },
          { number: '02', title: '', description: '' },
          { number: '03', title: '', description: '' },
        ] as unknown[],
        primaryCtaText: '',
        primaryCtaHref: '',
      }
  }
}

/**
 * Données de DÉMO réalistes utilisées par la route
 * `/preview/article-block-demo/[type]` pour montrer un rendu réaliste
 * du bloc dans le panneau « Ajouter un bloc ».
 *
 * Volontairement riches (pas vides) pour que la preview ait du sens. Les
 * IDs `mediaId` sont des chaînes factices ; le rendu doit gérer le fallback
 * quand le média n'est pas trouvé.
 */
export function getDemoBlockData(type: AddableBlockType): Record<string, unknown> {
  switch (type) {
    case 'HEADING':
      return { text: 'Un sous-titre éditorial qui structure votre article' }
    case 'PARAGRAPH':
      return {
        text:
          "Lorem ipsum **dolor sit amet**, consectetur adipiscing elit. Donec ultricies, _orci eget tincidunt facilisis_, nibh elit pulvinar dolor, ac mollis lectus mauris ac risus. Vivamus eu metus quis odio cursus tristique. [En savoir plus](#).",
      }
    case 'QUOTE':
      return {
        text:
          "Investir dans la durée, c'est faire confiance à la composition silencieuse du temps.",
        author: 'Anonyme',
      }
    case 'BULLET_LIST':
      return {
        items: [
          'Premier point clé énoncé brièvement',
          'Deuxième argument avec un détail concret',
          'Troisième élément qui conclut la liste',
        ],
      }
    case 'NUMBERED_LIST':
      return {
        items: [
          'Étape 1 : préparer les informations nécessaires',
          'Étape 2 : valider les conditions de souscription',
          'Étape 3 : finaliser et signer le document',
        ],
      }
    case 'VIDEO':
      return {
        url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        caption: 'Légende optionnelle de la vidéo affichée en dessous',
      }
    case 'DOCUMENT':
      return { mediaId: '', title: 'Document explicatif officiel.pdf' }
    case 'MEDIA_IMAGE_CAROUSEL': {
      // 6 images de démo via Picsum (URLs externes stables, hors médiathèque).
      // On fournit directement `carouselItems` au format enrichi attendu par
      // `ArticleBlockStream` (cf. case MEDIA_IMAGE_CAROUSEL) ; les `mediaId`
      // sont factices et ne servent que de clé React. `imageMediaIds` est
      // conservé en miroir au cas où un autre consommateur l'inspecte.
      const seeds = [
        'arq-demo-1',
        'arq-demo-2',
        'arq-demo-3',
        'arq-demo-4',
        'arq-demo-5',
        'arq-demo-6',
      ]
      return {
        moduleTitle: 'Galerie du projet',
        description: 'Quelques visuels représentatifs en carrousel.',
        imageMediaIds: seeds.map((s) => `demo-${s}`),
        carouselItems: seeds.map((seed, i) => ({
          mediaId: `demo-${seed}`,
          url: `https://picsum.photos/seed/${seed}/1200/750`,
          alt: `Image démo ${i + 1}`,
        })),
      }
    }
    case 'LOCALISATION':
      return {
        moduleTitle: 'Localisation',
        description: 'Adresse complète : 1 Place Vendôme, 75001 Paris',
        embedUrl:
          'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2624.9!2d2.329!3d48.867!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1',
      }
    case 'DOCUMENTS_LIST':
      return {
        moduleTitle: 'Documents officiels',
        subtitle: 'Pièces réglementaires',
        description: 'Téléchargez les documents associés à ce produit.',
        documentEntries: [
          { mediaId: '', documentName: 'DIC – Document d’information clé.pdf' },
          { mediaId: '', documentName: 'Statuts de la société.pdf' },
          { mediaId: '', documentName: "Note d'information AMF.pdf" },
        ],
      }
    case 'KEY_INFORMATION':
      return {
        title: 'Informations clés',
        ctaLabel: 'Découvrir l’offre',
        ctaHref: '#',
        rows: [
          { label: 'Capital minimum', value: '1 000 €' },
          { label: 'Fréquence des intérêts', value: 'Mensuelle' },
          { label: 'Durée recommandée', value: '5 ans' },
          { label: 'Disponibilité', value: 'France métropolitaine' },
        ],
      }
    case 'VIDEO_BLOCK_ARTICLE':
      // `VaultVideoBlockArticle` exige `posterImageUrl` (URL directe) ET un
      // YouTube ID valide pour afficher l'item ; sinon il est filtré.
      // Une seule vidéo en démo pour rester lisible dans le panneau preview.
      return {
        title: 'Vidéos associées',
        items: [
          {
            title: 'Présentation par le fondateur',
            videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            date: '12 mars 2025',
            posterImageUrl: 'https://picsum.photos/seed/arq-video-1/1200/675',
          },
        ],
      }
    case 'STEPS_MODULE':
      return {
        title: 'Calendrier de l’opération',
        subtitle: 'Les grandes étapes',
        description: 'Suivez la progression de votre placement étape par étape.',
        rightLabel: '',
        items: [
          {
            dayLabel: 'J–30',
            date: 'Terminé',
            title: 'Période de souscription',
            description: 'Ouverture aux investisseurs éligibles.',
            isCompleted: true,
          },
          {
            dayLabel: 'J',
            date: 'Aujourd’hui',
            title: 'Clôture de la souscription',
            description: 'Vérification des dossiers reçus.',
            isCompleted: true,
          },
          {
            dayLabel: 'J+30',
            date: 'À venir',
            title: 'Premier versement des intérêts',
            description: 'Versement mensuel sur le compte courant associé.',
            isCompleted: false,
          },
        ],
      }
    case 'HOW_IT_WORKS_CAROUSEL':
      return {
        label: 'COMMENT ÇA MARCHE',
        title: 'Découvrir le parcours en 3 étapes',
        subtitle: 'Un processus simple et transparent',
        hideStepNumbering: false,
        surface: 'light',
        steps: [
          {
            number: '01',
            title: 'Créez votre compte en ligne',
            description: 'Renseignez vos informations en quelques minutes, vérification rapide.',
          },
          {
            number: '02',
            title: 'Choisissez votre offre',
            description: 'Parcourez les opportunités disponibles et sélectionnez la vôtre.',
          },
          {
            number: '03',
            title: 'Suivez votre investissement',
            description: 'Tableau de bord en temps réel, intérêts mensuels.',
          },
        ],
        primaryCtaText: 'Commencer maintenant',
        primaryCtaHref: '#',
      }
  }
}
