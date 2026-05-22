/**
 * Mapping pur Projects → modules Vault Builder (vault_builder_v1).
 * Voir exclusiveOfferProjectMapping.md pour la table de correspondance officielle.
 */
import type { ContentStatus } from '@prisma/client'
import type { PackagedCommercialStatus } from '@prisma/client'

export type VaultModule = {
  id: string
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export type LandingConfigShape = {
  templateKey: string
  navbar: Record<string, unknown>
  pageTitle: { enabled: boolean; text: string }
  fixedBottomCta: Record<string, unknown>
  modules: VaultModule[]
  investmentTypeSlug?: string
  sortOrder: number
  headerMediaId?: string | null
}

const DEFAULT_NAVBAR = {
  leftIconType: 'back',
  leftRedirectType: 'back',
  leftTarget: '',
  rightAction: { icon: 'favorite', redirectType: 'none', target: '' },
}

export function mapProjectStatusToCommercial(status: ContentStatus): PackagedCommercialStatus {
  return status === 'PUBLISHED' ? 'PUBLISHED' : 'DRAFT'
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function moduleId(projectId: string, key: string): string {
  return `mig-${projectId}-${key}`
}

/** Parse competitiveAdvantages / i18n JSON → rows module CompetitiveAdvantagesModule */
export function mapCompetitiveAdvantagesJson(raw: unknown): {
  title: string
  rows: Array<Record<string, unknown>>
} {
  const o = asRecord(raw)
  if (!o) return { title: 'Pourquoi cette offre ?', rows: [] }
  const title = typeof o.title === 'string' ? o.title : 'Pourquoi cette offre ?'
  const rowsIn = Array.isArray(o.rows) ? o.rows : []
  const rows = rowsIn.map((r, i) => {
    const row = asRecord(r) ?? {}
    return {
      icon: typeof row.icon === 'string' ? row.icon : 'insights_rounded',
      iconBackgroundColor: typeof row.iconBackgroundColor === 'string' ? row.iconBackgroundColor : '#6B7280',
      category: typeof row.category === 'string' ? row.category : 'content',
      title: typeof row.title === 'string' ? row.title : `Point ${i + 1}`,
      description: typeof row.description === 'string' ? row.description : '',
    }
  })
  return { title, rows }
}

/** Parse keyInformation JSON → KeyInformationModule */
export function mapKeyInformationJson(raw: unknown): {
  title: string
  rows: Array<{ label: string; value: string; showInfoIcon: boolean; infoLinkArticle: string }>
} {
  const o = asRecord(raw)
  if (!o) return { title: 'Informations clés', rows: [] }
  const title = typeof o.title === 'string' ? o.title : 'Informations clés'
  const rowsIn = Array.isArray(o.rows) ? o.rows : []
  const rows = rowsIn.map((r) => {
    const row = asRecord(r) ?? {}
    const label = typeof row.label === 'string' ? row.label : ''
    const valueRaw = typeof row.value === 'string' ? row.value : ''
    const infoContent = typeof row.infoContent === 'string' ? row.infoContent : ''
    const value = infoContent && valueRaw ? `${valueRaw}\n\n${infoContent}` : valueRaw || infoContent
    return {
      label,
      value,
      showInfoIcon: Boolean(row.showInfoIcon),
      infoLinkArticle: typeof row.infoTitle === 'string' ? row.infoTitle : '',
    }
  })
  return { title, rows }
}

/** Parse howItWorks JSON → markdown secondaire */
export function mapHowItWorksToMarkdown(raw: unknown): { title: string; markdown: string } {
  const o = asRecord(raw)
  if (!o) return { title: 'Comment ça fonctionne', markdown: '' }
  const title = typeof o.title === 'string' ? o.title : 'Comment ça fonctionne'
  const content = typeof o.content === 'string' ? o.content : ''
  const links = Array.isArray(o.links) ? o.links : []
  let md = content
  if (links.length > 0) {
    md += '\n\n'
    for (const l of links) {
      const link = asRecord(l)
      if (link && typeof link.label === 'string' && typeof link.url === 'string') {
        md += `- [${link.label}](${link.url})\n`
      }
    }
  }
  return { title, markdown: md.trim() }
}

export function buildVaultModulesFromProject(input: {
  projectId: string
  title: string
  shortDescription: string | null
  description: string | null
  competitiveAdvantages: unknown
  howItWorks: unknown
  keyInformation: unknown
  faq: unknown
}): VaultModule[] {
  const modules: VaultModule[] = []

  modules.push({
    id: moduleId(input.projectId, 'title'),
    type: 'TitlePage',
    enabled: true,
    content: {
      title: input.title,
      subtitle: input.shortDescription ?? '',
    },
  })

  if (input.description?.trim()) {
    modules.push({
      id: moduleId(input.projectId, 'about'),
      type: 'SimpleMarkdownContentModule',
      enabled: true,
      content: {
        moduleTitle: 'À propos',
        markdown: input.description,
        links: [] as unknown[],
      },
    })
  }

  const comp = mapCompetitiveAdvantagesJson(input.competitiveAdvantages)
  if (comp.rows.length > 0) {
    modules.push({
      id: moduleId(input.projectId, 'advantages'),
      type: 'CompetitiveAdvantagesModule',
      enabled: true,
      content: {
        title: comp.title,
        rows: comp.rows,
      },
    })
  }

  const how = mapHowItWorksToMarkdown(input.howItWorks)
  if (how.markdown.length > 0) {
    modules.push({
      id: moduleId(input.projectId, 'how'),
      type: 'SimpleMarkdownContentModule',
      enabled: true,
      content: {
        moduleTitle: how.title,
        markdown: how.markdown,
        links: [],
      },
    })
  }

  const ki = mapKeyInformationJson(input.keyInformation)
  if (ki.rows.length > 0) {
    modules.push({
      id: moduleId(input.projectId, 'keyinfo'),
      type: 'KeyInformationModule',
      enabled: true,
      content: {
        title: ki.title,
        rows: ki.rows,
      },
    })
  }

  const faq = asRecord(input.faq)
  const faqItems = faq && Array.isArray(faq.items) ? faq.items : []
  const hcItems = faqItems
    .map((it) => asRecord(it))
    .filter((it): it is Record<string, unknown> => it != null)
    .filter((it) => typeof it.articleSlug === 'string' && it.articleSlug.length > 0)
    .map((it) => ({ articleSlug: it.articleSlug as string }))

  if (hcItems.length > 0) {
    modules.push({
      id: moduleId(input.projectId, 'faq'),
      type: 'FaqAccordionModule',
      enabled: true,
      content: {
        title: 'FAQ',
        footerLinkLabel: 'Centre d’aide',
        footerLinkUrl: '',
        footerCollectionSlug: 'getting-started',
        footerCategorySlug: 'investing-basics',
        footerFilterLabel: '',
        items: hcItems,
      },
    })
  }

  modules.push({
    id: moduleId(input.projectId, 'legal'),
    type: 'ContentBasDePageSansModuleBlanc',
    enabled: true,
    content: {
      markdown:
        'En participant à ce programme, vous confirmez avoir lu et accepté les [conditions générales](https://arquantix.com).',
    },
  })

  return modules
}

export function buildLandingConfig(input: {
  projectId: string
  pageTitleText: string
  headerMediaId: string | null
  investmentTypeSlug?: string
  modules: VaultModule[]
}): LandingConfigShape {
  return {
    templateKey: 'PageSimpleNavBarTopTitlePageContent',
    navbar: DEFAULT_NAVBAR,
    pageTitle: {
      enabled: true,
      text: input.pageTitleText,
    },
    fixedBottomCta: {
      enabled: false,
      label: '',
      redirectType: 'none',
      target: '',
    },
    modules: input.modules,
    investmentTypeSlug: input.investmentTypeSlug,
    sortOrder: 500,
    headerMediaId: input.headerMediaId ?? undefined,
  }
}
