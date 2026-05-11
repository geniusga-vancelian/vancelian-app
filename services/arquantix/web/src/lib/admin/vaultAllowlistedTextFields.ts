/**
 * Liste des champs texte allowlistés du Vault (aligné `vaultAutoTranslateModules`).
 * Utilisé par « Check all module language » (scan / correction DRAFT).
 */

import { shouldSkipPlainString } from '@/lib/admin/vaultAutoTranslateAllowlist'

export type VaultAllowlistedTextKind = 'plain' | 'markdown'

export type VaultAllowlistedTextField = {
  path: string
  textKind: VaultAllowlistedTextKind
  value: string
  moduleIndex?: number
  moduleType?: string
  /** Hors JSON vault (PageI18n). */
  scope: 'vault_root' | 'module' | 'page_i18n'
}

function pushField(
  out: VaultAllowlistedTextField[],
  partial: Omit<VaultAllowlistedTextField, 'value'> & { value: string | undefined | null },
): void {
  if (typeof partial.value !== 'string' || !partial.value.trim()) return
  if (shouldSkipPlainString(partial.value)) return
  out.push({
    ...partial,
    value: partial.value,
  } as VaultAllowlistedTextField)
}

function collectFromModuleContent(
  moduleIndex: number,
  moduleType: string,
  c: Record<string, unknown>,
  basePath: string,
  out: VaultAllowlistedTextField[],
): void {
  switch (moduleType) {
    case 'TitlePage':
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.subtitle`,
        textKind: 'plain',
        value: c.subtitle as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    case 'TagsModule': {
      const tags = Array.isArray(c.tags) ? c.tags : []
      tags.forEach((x, ti) => {
        if (typeof x === 'string') {
          pushField(out, {
            path: `${basePath}.tags[${ti}]`,
            textKind: 'plain',
            value: x,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'FundingModule': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.footnote`,
        textKind: 'plain',
        value: c.footnote as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const items = Array.isArray(c.items) ? c.items : []
      items.forEach((row, ri) => {
        if (row != null && typeof row === 'object') {
          const r = row as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.items[${ri}].label`,
            textKind: 'plain',
            value: r.label as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      if (c.manual && typeof c.manual === 'object') {
        const m = c.manual as Record<string, unknown>
        pushField(out, {
          path: `${basePath}.manual.rateDisplay`,
          textKind: 'plain',
          value: m.rateDisplay as string | undefined,
          moduleIndex,
          moduleType,
          scope: 'module',
        })
        pushField(out, {
          path: `${basePath}.manual.totalDisplay`,
          textKind: 'plain',
          value: m.totalDisplay as string | undefined,
          moduleIndex,
          moduleType,
          scope: 'module',
        })
      }
      return
    }
    case 'SimpleMarkdownContentModule': {
      pushField(out, {
        path: `${basePath}.moduleTitle`,
        textKind: 'plain',
        value: c.moduleTitle as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.markdown`,
        textKind: 'markdown',
        value: c.markdown as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const links = Array.isArray(c.links) ? c.links : []
      links.forEach((link, li) => {
        if (link != null && typeof link === 'object') {
          const l = link as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.links[${li}].label`,
            textKind: 'plain',
            value: l.label as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'CompetitiveAdvantagesModule': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const rows = Array.isArray(c.rows) ? c.rows : []
      rows.forEach((row, ri) => {
        if (row != null && typeof row === 'object') {
          const r = row as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.rows[${ri}].title`,
            textKind: 'plain',
            value: r.title as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
          pushField(out, {
            path: `${basePath}.rows[${ri}].description`,
            textKind: 'plain',
            value: r.description as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'FaqAccordionModule': {
      ;['title', 'intro', 'footerLinkLabel', 'footerFilterLabel'].forEach((k) => {
        pushField(out, {
          path: `${basePath}.${k}`,
          textKind: 'plain',
          value: c[k] as string | undefined,
          moduleIndex,
          moduleType,
          scope: 'module',
        })
      })
      return
    }
    case 'ContentBasDePageSansModuleBlanc':
      pushField(out, {
        path: `${basePath}.markdown`,
        textKind: 'markdown',
        value: c.markdown as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    case 'MarktingCardLargePortrait':
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    case 'MarketingCardsSmallCarouselModule':
    case 'MarketingCardsSmallSlidingCarrousel_Portrait':
    case 'MarketingCardsSmallSlidingCarrousel_Paysage': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const items = Array.isArray(c.items) ? c.items : []
      items.forEach((item, ii) => {
        if (item != null && typeof item === 'object') {
          const it = item as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.items[${ii}].title`,
            textKind: 'plain',
            value: it.title as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
          pushField(out, {
            path: `${basePath}.items[${ii}].description`,
            textKind: 'plain',
            value: it.description as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'TransactionLatest10Module':
    case 'BlogALaUne':
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    case 'AllocationModule': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.introText`,
        textKind: 'plain',
        value: c.introText as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const slices = Array.isArray(c.slices) ? c.slices : []
      slices.forEach((sl, si) => {
        if (sl != null && typeof sl === 'object') {
          const s = sl as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.slices[${si}].label`,
            textKind: 'plain',
            value: s.label as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'KeyInformationModule': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.ctaLabel`,
        textKind: 'plain',
        value: c.ctaLabel as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const rows = Array.isArray(c.rows) ? c.rows : []
      rows.forEach((row, ri) => {
        if (row != null && typeof row === 'object') {
          const r = row as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.rows[${ri}].label`,
            textKind: 'plain',
            value: r.label as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
          const v = r.value
          if (typeof v === 'string' && v.trim() && !shouldSkipPlainString(v)) {
            pushField(out, {
              path: `${basePath}.rows[${ri}].value`,
              textKind: 'plain',
              value: v,
              moduleIndex,
              moduleType,
              scope: 'module',
            })
          }
        }
      })
      return
    }
    case 'MediaImageCarouselModule':
    case 'DocumentsListModule': {
      pushField(out, {
        path: `${basePath}.moduleTitle`,
        textKind: 'plain',
        value: c.moduleTitle as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.description`,
        textKind: 'plain',
        value: c.description as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      if (moduleType === 'DocumentsListModule') {
        pushField(out, {
          path: `${basePath}.subtitle`,
          textKind: 'plain',
          value: c.subtitle as string | undefined,
          moduleIndex,
          moduleType,
          scope: 'module',
        })
      }
      if (moduleType === 'DocumentsListModule' && Array.isArray(c.documentEntries)) {
        c.documentEntries.forEach((entry, ei) => {
          if (entry != null && typeof entry === 'object') {
            const e = entry as Record<string, unknown>
            pushField(out, {
              path: `${basePath}.documentEntries[${ei}].documentName`,
              textKind: 'plain',
              value: e.documentName as string | undefined,
              moduleIndex,
              moduleType,
              scope: 'module',
            })
          }
        })
      }
      return
    }
    case 'PerformanceChart':
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    case 'StepsModule': {
      ;['title', 'subtitle', 'description', 'rightLabel'].forEach((k) => {
        pushField(out, {
          path: `${basePath}.${k}`,
          textKind: 'plain',
          value: c[k] as string | undefined,
          moduleIndex,
          moduleType,
          scope: 'module',
        })
      })
      const items = Array.isArray(c.items) ? c.items : []
      items.forEach((item, ii) => {
        if (item != null && typeof item === 'object') {
          const it = item as Record<string, unknown>
          ;['dayLabel', 'date', 'title', 'description'].forEach((k) => {
            pushField(out, {
              path: `${basePath}.items[${ii}].${k}`,
              textKind: 'plain',
              value: it[k] as string | undefined,
              moduleIndex,
              moduleType,
              scope: 'module',
            })
          })
          const tags = Array.isArray(it.tags) ? it.tags : []
          tags.forEach((t, ti) => {
            if (typeof t === 'string') {
              pushField(out, {
                path: `${basePath}.items[${ii}].tags[${ti}]`,
                textKind: 'plain',
                value: t,
                moduleIndex,
                moduleType,
                scope: 'module',
              })
            }
          })
        }
      })
      return
    }
    case 'VideoBlockArticleModule': {
      pushField(out, {
        path: `${basePath}.title`,
        textKind: 'plain',
        value: c.title as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      const items = Array.isArray(c.items) ? c.items : []
      items.forEach((item, ii) => {
        if (item != null && typeof item === 'object') {
          const it = item as Record<string, unknown>
          pushField(out, {
            path: `${basePath}.items[${ii}].title`,
            textKind: 'plain',
            value: it.title as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
          pushField(out, {
            path: `${basePath}.items[${ii}].date`,
            textKind: 'plain',
            value: it.date as string | undefined,
            moduleIndex,
            moduleType,
            scope: 'module',
          })
        }
      })
      return
    }
    case 'LocalisationModule': {
      pushField(out, {
        path: `${basePath}.moduleTitle`,
        textKind: 'plain',
        value: c.moduleTitle as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.description`,
        textKind: 'plain',
        value: c.description as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    }
    case 'VirtualVisualizationModule': {
      pushField(out, {
        path: `${basePath}.moduleTitle`,
        textKind: 'plain',
        value: c.moduleTitle as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      pushField(out, {
        path: `${basePath}.description`,
        textKind: 'plain',
        value: c.description as string | undefined,
        moduleIndex,
        moduleType,
        scope: 'module',
      })
      return
    }
    default:
      return
  }
}

/**
 * Champs texte allowlistés pour analyse linguistique / correction (vault JSON + PageI18n optionnel).
 */
export function collectAllowlistedVaultTextFields(
  data: Record<string, unknown>,
  pageI18n?: { title: string | null; description: string | null },
): VaultAllowlistedTextField[] {
  const out: VaultAllowlistedTextField[] = []

  if (data.pageTitle && typeof data.pageTitle === 'object') {
    const pt = data.pageTitle as Record<string, unknown>
    pushField(out, {
      path: 'pageTitle.text',
      textKind: 'plain',
      value: pt.text as string | undefined,
      scope: 'vault_root',
    })
  }
  if (data.fixedBottomCta && typeof data.fixedBottomCta === 'object') {
    const fb = data.fixedBottomCta as Record<string, unknown>
    pushField(out, {
      path: 'fixedBottomCta.label',
      textKind: 'plain',
      value: fb.label as string | undefined,
      scope: 'vault_root',
    })
  }

  const modules = Array.isArray(data.modules) ? data.modules : []
  modules.forEach((mod, mi) => {
    if (mod == null || typeof mod !== 'object') return
    const m = mod as Record<string, unknown>
    const typ = typeof m.type === 'string' ? m.type : 'unknown'
    const content =
      m.content != null && typeof m.content === 'object' && !Array.isArray(m.content)
        ? (m.content as Record<string, unknown>)
        : {}
    const basePath = `modules[${mi}].content`
    collectFromModuleContent(mi, typ, content, basePath, out)
  })

  if (pageI18n) {
    pushField(out, {
      path: 'pageI18n.title',
      textKind: 'plain',
      value: pageI18n.title ?? undefined,
      scope: 'page_i18n',
    })
    pushField(out, {
      path: 'pageI18n.description',
      textKind: 'plain',
      value: pageI18n.description ?? undefined,
      scope: 'page_i18n',
    })
  }

  return out
}
