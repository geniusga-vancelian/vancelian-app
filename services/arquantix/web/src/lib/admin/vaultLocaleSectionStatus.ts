import { ContentStatus } from '@prisma/client'

import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'

/**
 * État éditorial du SectionContent vault (`vault_builder_v1`) par langue — uniquement côté admin.
 */
export type VaultLocaleLayerKind = 'empty' | 'draft_only' | 'published_only' | 'draft_and_published'

export type VaultLocaleLayerInfo = {
  kind: VaultLocaleLayerKind
  /** Si les deux couches existent : le JSON est-il identique (sérialisation stable simple). */
  draftMatchesPublished: boolean | null
}

function stableJsonString(value: unknown): string {
  try {
    return JSON.stringify(value)
  } catch {
    return ''
  }
}

/**
 * À partir des lignes SectionContent d’une section vault, calcule l’état par locale.
 */
export function computeVaultLocaleLayerInfos(
  contents: Array<{ locale: string; status: ContentStatus; data: unknown }>,
): Record<Locale, VaultLocaleLayerInfo> {
  const out = {} as Record<Locale, VaultLocaleLayerInfo>
  for (const loc of supportedLocales) {
    const draft = contents.find((c) => c.locale === loc && c.status === ContentStatus.DRAFT)
    const pub = contents.find((c) => c.locale === loc && c.status === ContentStatus.PUBLISHED)
    const hasD = draft != null
    const hasP = pub != null
    let kind: VaultLocaleLayerKind
    if (!hasD && !hasP) kind = 'empty'
    else if (hasD && !hasP) kind = 'draft_only'
    else if (!hasD && hasP) kind = 'published_only'
    else kind = 'draft_and_published'

    let draftMatchesPublished: boolean | null = null
    if (kind === 'draft_and_published') {
      draftMatchesPublished = stableJsonString(draft?.data) === stableJsonString(pub?.data)
    }

    out[loc] = { kind, draftMatchesPublished }
  }
  return out
}

/** Libellé court pour badge UI (FR). */
export function vaultLocaleLayerBadgeLabel(info: VaultLocaleLayerInfo): string {
  switch (info.kind) {
    case 'empty':
      return 'Vide'
    case 'draft_only':
      return 'Brouillon seulement'
    case 'published_only':
      return 'Publié seulement'
    case 'draft_and_published':
      return info.draftMatchesPublished ? 'Brouillon + Publié (identiques)' : 'Brouillon + Publié (différents)'
    default:
      return '—'
  }
}
