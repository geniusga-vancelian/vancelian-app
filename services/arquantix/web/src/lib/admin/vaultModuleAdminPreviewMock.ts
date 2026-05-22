/**
 * Contenu fictif pour l’aperçu « Ajouter un module » du Vault Builder (sans Prisma ni page réelle).
 * Les champs sont enrichis pour correspondre au format attendu par {@link VaultModuleWeb} / l’API publique.
 */
import { getVaultModuleDefaultContent } from '@/lib/admin/vaultModuleCatalog'
import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'

const PREVIEW_MODULE_ID = 'admin-vault-module-preview'

const PICSUM = (seed: string, w: number, h: number) =>
  `https://picsum.photos/seed/${seed}/${w}/${h}`

function applyPreviewEnrichments(
  moduleType: string,
  base: Record<string, unknown>,
): Record<string, unknown> {
  switch (moduleType) {
    case 'TitlePage':
      return {
        ...base,
        title: 'Titre de démonstration (aperçu)',
        subtitle: 'Sous-titre factice — le rendu final dépend aussi du hero de la fiche.',
      }

    case 'TagsModule':
      return {
        ...base,
        tags: ['Tag A', 'Tag B', 'Aperçu'],
      }

    case 'FundingModule':
      return {
        ...base,
        title: 'Financement (aperçu)',
        displayMode: 'manual',
        footnote: '_Données factices pour prévisualiser les cartes._',
        manual: { progressPct: 58, rateDisplay: '10,5 % APR', totalDisplay: '1,2 M € / 2 M €' },
        _resolved: {
          progressPct: 58,
          rateDisplay: '10,5 % APR',
          totalDisplay: '1,2 M € / 2 M €',
        },
      }

    case 'MediaImageCarouselModule':
      return {
        ...base,
        moduleTitle: 'Carrousel (aperçu)',
        description: 'Images factices — non liées à votre médiathèque.',
        carouselItems: [
          { mediaId: 'demo-carousel-1', url: PICSUM('vault-cr-1', 1200, 800), alt: 'Visuel 1' },
          { mediaId: 'demo-carousel-2', url: PICSUM('vault-cr-2', 1200, 800), alt: 'Visuel 2' },
        ],
      }

    case 'DocumentsListModule':
      return {
        ...base,
        moduleTitle: 'Documents (aperçu)',
        description: 'Exemple de liste — un PDF public de test.',
        subtitle: '',
        documentItems: [
          {
            mediaId: 'demo-doc-1',
            downloadUrl: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
            displayName: 'Document-exemple.pdf',
            dateLabel: '2026',
          },
        ],
      }

    case 'VideoBlockArticleModule': {
      const items = Array.isArray(base.items) ? [...base.items] : []
      const first =
        items[0] != null && typeof items[0] === 'object'
          ? { ...(items[0] as Record<string, unknown>) }
          : {}
      return {
        ...base,
        title: typeof base.title === 'string' && base.title.trim() ? base.title : 'Vidéos (aperçu)',
        items: [
          {
            ...first,
            title: 'Vidéo de démonstration',
            videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            date: '6 mai 2026',
            posterImageUrl: PICSUM('vault-video-poster', 1280, 720),
          },
        ],
      }
    }

    case 'LocalisationModule':
      return {
        ...base,
        moduleTitle: 'Localisation (aperçu)',
        description:
          'Texte d’exemple. La carte ci-dessous est une iframe Google Maps de démonstration.',
        embedUrl:
          'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d83982.88784439989!2d2.3488!3d48.8534!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x47e671d877937b0f%3A0xb975cc456368b1dd!2sParis!5e0!3m2!1sen!2sfr!4v1710000000000!5m2!1sen!2sfr',
      }

    case 'VirtualVisualizationModule':
      return {
        ...base,
        moduleTitle: 'Visite virtuelle (aperçu)',
        description:
          'Données de démonstration — le viewer ci-dessous charge un exemple public Koma Visualization.',
        visualizationUrl:
          'https://virtual.komavisualization.com/vrViewer/b1c04f2e-5dd7-41ef-be4e-988ee110a14c/',
      }

    case 'SimpleMarkdownContentModule':
      return {
        ...base,
        moduleTitle: 'Texte (aperçu)',
        markdown:
          'Ceci est un **aperçu** avec données factices. Les listes et liens permettent de valider le rendu Markdown.\n\n- Point un\n- Point deux\n\n[Lien exemple](https://arquantix.com)',
        links: [{ label: 'Lien de démo', url: 'https://arquantix.com' }],
      }

    case 'CompetitiveAdvantagesModule':
      return {
        ...base,
        title: 'Atouts (aperçu)',
      }

    case 'KeyInformationModule':
      return {
        ...base,
        title: 'Informations clés (aperçu)',
        ctaLabel: 'En savoir plus',
        ctaHref: '/help',
      }

    case 'StepsModule':
      return {
        ...base,
        title: 'Calendrier (aperçu)',
        subtitle: 'Étapes factices pour la timeline.',
        rightLabel: 'Horizon',
        items: [
          {
            dayLabel: 'T1',
            date: 'Jan. 2026',
            title: 'Lancement',
            description: 'Première étape — données de démonstration uniquement.',
            tags: ['Kickoff'],
          },
          {
            dayLabel: 'T2',
            date: 'Juin 2026',
            title: 'Milestone intermédiaire',
            description: 'Suite du calendrier projet.',
            tags: [],
          },
          {
            dayLabel: 'T3',
            date: 'Déc. 2026',
            title: 'Clôture prévue',
            description: 'Dernière étape affichée dans cet aperçu.',
            tags: ['Livraison'],
          },
        ],
      }

    case 'FaqAccordionModule':
      return {
        ...base,
        title: 'FAQ (aperçu)',
        intro:
          'Les questions réelles sont chargées depuis Help en production. Ici, exemple de rendu accordéon DS.',
        footerLinkLabel: 'Voir les articles d’aide',
        footerLinkUrl: '',
        footerCollectionSlug: 'getting-started',
        footerCategorySlug: 'investing-basics',
        items: [
          {
            question: 'Comment fonctionne cette offre ?',
            standfirst:
              'Il s’agit d’un aperçu factice. En production, les réponses proviennent des articles Help liés.',
          },
          {
            question: 'Quel est le rendement visé ?',
            standfirst: 'Le rendement affiché dans le module Funding est indicatif pour la démo.',
          },
        ],
      }

    case 'ContentBasDePageSansModuleBlanc':
      return {
        ...base,
        markdown:
          '**Mentions (aperçu)** — texte légal fictif. [Conditions](https://arquantix.com) pour valider le rendu.',
      }

    default:
      return base
  }
}

/**
 * Module `VaultModulePublic` prêt pour {@link VaultModuleWeb} dans la modale d’ajout.
 */
export function buildVaultModulePreviewMock(moduleType: string): VaultModulePublic {
  const base = getVaultModuleDefaultContent(moduleType)
  const content = applyPreviewEnrichments(moduleType, base)

  return {
    id: PREVIEW_MODULE_ID,
    type: moduleType,
    enabled: true,
    content,
  }
}
