/**
 * Dubai Real Estate Yield Strategy — contenu injectable (Project / ProjectI18n).
 * Slug stable : exclusive-offer-import
 *
 * Note FAQ : le module FAQ Flutter attend des articles Help Center (articleSlug, collectionSlug…).
 * Les questions / réponses métier sont donc rendues en Markdown dans `description` (section dédiée).
 */

import type { ContentStatus, Prisma } from '@prisma/client'

export const EXCLUSIVE_OFFER_IMPORT_SLUG = 'exclusive-offer-import'

export type ExclusiveOfferProjectTemplate = {
  slug: string
  status: ContentStatus
  investmentCategory: string | null
  youtubeUrl: string | null
  i18n: {
    locale: string
    title: string
    location: string | null
    shortDescription: string
    description: string
    metaTitle: string | null
    metaDescription: string | null
    descriptionLinks: Prisma.InputJsonValue
    howItWorks: Prisma.InputJsonValue
    keyInformation: Prisma.InputJsonValue
    competitiveAdvantages: Prisma.InputJsonValue
    faq: Prisma.InputJsonValue
  }
}

export function getExclusiveOfferProjectTemplate(): ExclusiveOfferProjectTemplate {
  return {
    slug: EXCLUSIVE_OFFER_IMPORT_SLUG,
    status: 'PUBLISHED',
    investmentCategory: 'Real estate',
    youtubeUrl: null,
    i18n: {
      locale: 'fr',
      title: 'Dubai Real Estate Yield Strategy',
      location: 'Dubaï, Émirats Arabes Unis',
      shortDescription:
        'Stratégie immobilière à Dubaï visant des revenus attractifs via l’acquisition et la valorisation d’actifs premium, dans un marché soutenu et une demande locative robuste.',
      description: [
        '## Vue d’ensemble',
        '',
        'Investissez dans une stratégie immobilière à Dubaï visant à générer des revenus attractifs via l’acquisition et la valorisation d’actifs premium dans une zone à forte croissance.',
        '',
        'Cette opportunité s’inscrit dans un contexte de dynamisme économique soutenu des Émirats Arabes Unis, avec une demande locative robuste et un environnement fiscal favorable aux investisseurs internationaux.',
        '',
        '## Pourquoi cette opportunité',
        '',
        '- Marché immobilier en forte croissance à Dubaï',
        '- Absence de fiscalité sur les revenus locatifs (selon la législation applicable et votre situation)',
        '- Demande soutenue sur les segments premium',
        '- Positionnement sur des actifs à fort potentiel de valorisation',
        '- Accès à une stratégie habituellement réservée à des investisseurs institutionnels',
        '',
        '## Risques',
        '',
        '- Risque de marché immobilier (variation des prix)',
        '- Risque de liquidité (sortie non immédiate)',
        '- Risque opérationnel lié à la gestion des actifs',
        '- Risque macro-économique régional',
        '',
        '## Liquidité',
        '',
        '- Horizon d’investissement : moyen / long terme',
        '- Liquidité : limitée pendant la durée du projet',
        '- Sortie dépendante de la stratégie (revente / distribution)',
        '',
        '## Déclarations et conformité',
        '',
        '- Investissement réservé à des investisseurs informés',
        '- Acceptation des risques liés aux actifs non cotés',
        '- Vérification KYC / AML requise',
        '',
        '## Questions fréquentes',
        '',
        '**Quel est l’objectif de cette stratégie ?**',
        '',
        'Générer un rendement via l’immobilier à Dubaï, en combinant revenus locatifs et valorisation.',
        '',
        '**Puis-je sortir à tout moment ?**',
        '',
        'Non, l’investissement est structuré sur un horizon défini avec une liquidité limitée.',
        '',
        '**Quels sont les principaux risques ?**',
        '',
        'Principalement le marché immobilier, la liquidité et la performance des actifs sélectionnés.',
      ].join('\n'),
      metaTitle: 'Dubai Real Estate Yield Strategy | Arquantix',
      metaDescription:
        'Stratégie immobilière à Dubaï : acquisition et valorisation d’actifs premium, marché dynamique et demande locative robuste.',
      descriptionLinks: [] as Prisma.InputJsonValue,
      howItWorks: {
        title: 'Comment ça fonctionne',
        content: [
          '1. Identification d’actifs immobiliers à fort potentiel à Dubaï',
          '2. Acquisition via une structure dédiée',
          '3. Optimisation et gestion des actifs',
          '4. Génération de revenus locatifs et/ou valorisation à la revente',
          '5. Redistribution des performances aux investisseurs',
        ].join('\n\n'),
        links: [],
      } as Prisma.InputJsonValue,
      keyInformation: {
        title: 'Informations clés',
        rows: [
          {
            categoryKey: 'asset_type',
            label: 'Type d’actif',
            value: 'Immobilier',
            showInfoIcon: false,
            infoTitle: null,
            infoContent: null,
          },
          {
            categoryKey: 'location',
            label: 'Localisation',
            value: 'Dubaï, Émirats Arabes Unis',
            showInfoIcon: false,
            infoTitle: null,
            infoContent: null,
          },
          {
            categoryKey: 'strategy',
            label: 'Stratégie',
            value: 'Acquisition et valorisation d’actifs immobiliers',
            showInfoIcon: true,
            infoTitle: 'Stratégie',
            infoContent:
              'La mise en œuvre opérationnelle et la structure juridique sont décrites dans la documentation remise aux investisseurs.',
          },
          {
            categoryKey: 'currency',
            label: 'Devise',
            value: 'USD / AED (à confirmer selon la structuration finale)',
            showInfoIcon: true,
            infoTitle: 'Devise',
            infoContent:
              'La devise effective et les mécanismes de change éventuels figurent dans la documentation contractuelle.',
          },
          {
            categoryKey: 'min_ticket',
            label: 'Ticket minimum',
            value: 'Indiqué dans l’offre commerciale et la documentation réglementaire.',
            showInfoIcon: true,
            infoTitle: 'Ticket',
            infoContent:
              'Le ticket applicable est communiqué dans les documents d’information et au moment de la souscription.',
          },
          {
            categoryKey: 'duration',
            label: 'Durée d’investissement',
            value: 'Précisée dans la documentation contractuelle.',
            showInfoIcon: true,
            infoTitle: 'Durée',
            infoContent:
              'L’horizon et les jalons sont définis contractuellement ; ils ne sont pas reproduits ici sous forme de chiffre unique sans document de référence.',
          },
          {
            categoryKey: 'target_return',
            label: 'Rendement cible',
            value: 'Non garanti ; objectif et hypothèses décrits dans la documentation.',
            showInfoIcon: true,
            infoTitle: 'Rendement',
            infoContent:
              'Aucun rendement n’est garanti. Toute projection provient exclusivement de la documentation officielle.',
          },
          {
            categoryKey: 'exit',
            label: 'Modalités de sortie',
            value: 'Conformément à la documentation contractuelle (revente, distribution, etc.).',
            showInfoIcon: true,
            infoTitle: 'Sortie',
            infoContent:
              'Les modalités de liquidité et de sortie sont fixées dans les instruments juridiques applicables.',
          },
        ],
      } as Prisma.InputJsonValue,
      competitiveAdvantages: {
        title: 'Atouts',
        rows: [
          {
            icon: 'apartment_rounded',
            iconBackgroundColor: '#1E88E5',
            title: 'Marché international dynamique',
            description:
              'Accès à un marché immobilier international en développement, avec une lecture locale des segments porteurs.',
          },
          {
            icon: 'assignment_turned_in_rounded',
            iconBackgroundColor: '#43A047',
            title: 'Structuration investisseur',
            description: 'Structuration pensée pour offrir une expérience d’investissement claire et encadrée.',
          },
          {
            icon: 'trending_up_rounded',
            iconBackgroundColor: '#FB8C00',
            title: 'Diversification de portefeuille',
            description:
              'Opportunité diversifiante au sein d’un portefeuille crypto ou traditionnel, selon votre allocation.',
          },
          {
            icon: 'insights_rounded',
            iconBackgroundColor: '#5E35B1',
            title: 'Sélection et gestion',
            description:
              'Appui sur une expertise locale pour la sélection des actifs et le suivi de la gestion.',
          },
        ],
      } as Prisma.InputJsonValue,
      faq: {
        enableTagRedirect: false,
        tagRedirectLabel: null,
        items: [],
      } as Prisma.InputJsonValue,
    },
  }
}
