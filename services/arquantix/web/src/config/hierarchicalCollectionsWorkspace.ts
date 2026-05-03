import { Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { helpCollectionIconMeta } from '@/config/helpCollectionDsIcons'

export type HierarchicalWorkspaceKind = 'help' | 'academy'

/** Options d’icônes Academy (admin), alignées sur l’API `iconKey`. */
export const ACADEMY_COLLECTION_ICON_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'school', label: 'School (académie)' },
  { value: 'library', label: 'Library' },
  { value: 'lightbulb', label: 'Lightbulb' },
  { value: 'play', label: 'Play (vidéo)' },
  { value: 'compass', label: 'Compass (guide)' },
  { value: 'trending-up', label: 'Trending up' },
  { value: 'shield', label: 'Shield' },
  { value: 'article', label: 'Article' },
  { value: 'help-circle', label: 'Help circle' },
]

export function collectionIconDisplay(
  kind: HierarchicalWorkspaceKind,
  iconKey: string,
): { Icon: LucideIcon; label: string } {
  if (kind === 'help') {
    const meta = helpCollectionIconMeta(iconKey)
    return { Icon: meta?.Icon ?? Sparkles, label: meta?.label ?? iconKey }
  }
  const opt = ACADEMY_COLLECTION_ICON_OPTIONS.find((o) => o.value === iconKey)
  return { Icon: Sparkles, label: opt?.label ?? iconKey }
}

export interface HierarchicalWorkspaceConfig {
  kind: HierarchicalWorkspaceKind
  apiBase: string
  translateApiPath: string
  approveEntityType: 'HELP_COLLECTION' | 'ACADEMY_COLLECTION'
  supportsCoverMedia: boolean
  defaultNewIconKey: string
  /** Sélecteur Lucide DS (Help) ou liste native (Academy). */
  iconMode: 'help_ds' | 'academy_native'
  styleBlocSubtitle: string
  slugCheckErrorSuffix: string
}

export const HIERARCHICAL_COLLECTIONS_CONFIG: Record<
  HierarchicalWorkspaceKind,
  HierarchicalWorkspaceConfig
> = {
  help: {
    kind: 'help',
    apiBase: '/api/admin/help/collections',
    translateApiPath: '/api/admin/translate/help-collection',
    approveEntityType: 'HELP_COLLECTION',
    supportsCoverMedia: true,
    defaultNewIconKey: 'article',
    iconMode: 'help_ds',
    styleBlocSubtitle: 'Style liste FAQ (mobile + web)',
    slugCheckErrorSuffix:
      'Exécutez les migrations Prisma (schéma Help à jour) puis réessayez.',
  },
  academy: {
    kind: 'academy',
    apiBase: '/api/admin/academy/collections',
    translateApiPath: '/api/admin/translate/academy-collection',
    approveEntityType: 'ACADEMY_COLLECTION',
    supportsCoverMedia: false,
    defaultNewIconKey: 'school',
    iconMode: 'academy_native',
    styleBlocSubtitle: 'Style liste Academy (mobile + web)',
    slugCheckErrorSuffix: 'Vérifiez que les migrations Academy sont appliquées.',
  },
}
