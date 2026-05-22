import type { FigmaStatItem } from '@/components/design-system/extracted'
import { Container } from '@/components/ui/Container'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import {
  VProofStats,
  type VProofStat,
} from '@/components/design-system/vancelian'

export interface SectionFigmaStatsGridProps {
  eyebrow?: string
  title?: string
  description?: string
  stats?: FigmaStatItem[]
  /** Legacy CMS — colonnes 3/4/6 (le DS Vancelian centre la grille de stats automatiquement). */
  columns?: 3 | 4 | 6
}

/**
 * Grille de stats CMS Figma — Vancelian Design System.
 *
 * Délègue à {@link VProofStats} (pattern `proof-bar` variant stats).
 * Les `columns` du CMS legacy sont ignorées : le DS centre naturellement
 * la grille avec un gap proportionnel au nombre d'entrées.
 */
export function SectionFigmaStatsGrid({
  eyebrow,
  title,
  description,
  stats = [],
}: SectionFigmaStatsGridProps) {
  const list: VProofStat[] = stats
    .filter((s) => s.value?.trim() || s.label?.trim())
    .map((s) => ({
      value: s.value?.trim() || '—',
      caption: s.label?.trim() || '',
    }))
  const hasHeader = Boolean(
    eyebrow?.trim() || title?.trim() || description?.trim(),
  )

  if (list.length === 0 && !hasHeader) return null

  return (
    <section className="w-full bg-v-bg py-20 lg:py-24">
      <Container className="flex flex-col items-center">
        <SectionFigmaBlockHeader
          eyebrow={eyebrow}
          title={title}
          description={description}
          titleSize="module"
        />
        {list.length > 0 ? (
          <div className="w-full pt-4">
            {/* VProofStats embarque sa propre `<section>` et son fond → on annule
                visuellement en rendant l'inner directement via le composant
                avec backgroundColor transparent. */}
            <VProofStats
              stats={list}
              tone="light"
              backgroundColor="transparent"
            />
          </div>
        ) : null}
      </Container>
    </section>
  )
}
