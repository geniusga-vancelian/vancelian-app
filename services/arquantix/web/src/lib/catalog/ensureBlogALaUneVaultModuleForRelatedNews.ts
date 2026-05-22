/**
 * Détail catalogue mobile : si la version résolue du vault (souvent PUBLISHED) ne contient
 * pas encore `BlogALaUne` alors que des articles Related→vault existent, on complète depuis
 * le **brouillon** de même locale lorsqu’il contient ce module (cas courant après ajout en
 * builder sans republication complète du JSON publié).
 */
import { ContentStatus } from '@prisma/client'

import {
  enrichVaultModulesForMobileClient,
  type VaultModulePublic,
} from '@/lib/cms/exclusiveOfferVaultPage'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'
import { normalizeVaultModulesFromSectionData } from '@/lib/vault/normalizeVaultModules'

function isBlogAlaUneType(raw: string): boolean {
  const t = raw.trim().toLowerCase()
  return t === 'blogalaune' || t === 'blog_a_la_une'
}

function normalizedModulesIncludeBlogALaUne(modules: VaultModulePublic[]): boolean {
  for (const m of modules) {
    if (!m.enabled) continue
    if (isBlogAlaUneType(m.type)) return true
  }
  return false
}

async function normalizeDraftBlogALaUneOnly(
  context: string,
  draftRootData: Record<string, unknown>,
): Promise<VaultModulePublic[]> {
  const { modules } = normalizeVaultModulesFromSectionData(draftRootData, context)
  return modules.filter((m) => m.enabled && isBlogAlaUneType(m.type))
}

type VaultSectionContentRow = {
  locale: string
  status: ContentStatus
  data: unknown
}

/**
 * Complète {@link vaultData} avec les modules BlogALaUne issus du brouillon lorsque nécessaire.
 */
export async function ensureBlogALaUneFromDraftWhenRelatedNews(
  prisma: Parameters<typeof enrichVaultModulesForMobileClient>[0],
  options: {
    sectionContents: VaultSectionContentRow[]
    vaultData: Record<string, unknown> | null
    /** Nombre d’articles liés au vault renvoyés au client (>0 déclenche la fusion). */
    relatedArticleCount: number
    requestedLocale: string
    defaultLocale: string
    publicOrigin: string | null
    contextSlug: string
    /**
     * Quand true : fusion uniquement depuis le brouillon (sans `enrichVaultModulesForMobileClient`).
     * À utiliser lorsque la chaîne d’enrichissement (ex. page web SSR) sera appliquée ensuite.
     */
    mergeDraftBlogOnly?: boolean
  },
): Promise<Record<string, unknown> | null> {
  const {
    sectionContents,
    vaultData,
    relatedArticleCount,
    requestedLocale,
    defaultLocale,
    publicOrigin,
    contextSlug,
    mergeDraftBlogOnly = false,
  } = options

  if (relatedArticleCount <= 0 || !vaultData || !Array.isArray(vaultData.modules)) {
    return vaultData
  }

  const mods = vaultData.modules as VaultModulePublic[]
  if (normalizedModulesIncludeBlogALaUne(mods)) {
    return vaultData
  }

  const draftRow = resolveVaultSectionContent(sectionContents, {
    requestedLocale,
    defaultLocale,
    mode: ContentStatus.DRAFT,
  })
  if (!draftRow || draftRow.data == null || typeof draftRow.data !== 'object') {
    return vaultData
  }

  const draftExtras = await normalizeDraftBlogALaUneOnly(
    `${contextSlug}:draft-blogalaune`,
    draftRow.data as Record<string, unknown>,
  )

  if (draftExtras.length === 0) {
    return vaultData
  }

  const merged = [...mods, ...draftExtras]
  if (mergeDraftBlogOnly) {
    return { ...vaultData, modules: merged }
  }
  const enriched = await enrichVaultModulesForMobileClient(prisma, merged, publicOrigin)
  return { ...vaultData, modules: enriched }
}
