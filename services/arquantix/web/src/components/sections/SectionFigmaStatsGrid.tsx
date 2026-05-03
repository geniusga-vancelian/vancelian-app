import { FigmaStatsGrid, type FigmaStatItem } from '@/components/design-system/extracted'
import { Container } from '@/components/ui/Container'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'

export interface SectionFigmaStatsGridProps {
  eyebrow?: string
  title?: string
  description?: string
  stats?: FigmaStatItem[]
  columns?: 3 | 4 | 6
}

export function SectionFigmaStatsGrid({
  eyebrow,
  title,
  description,
  stats = [],
  columns = 3,
}: SectionFigmaStatsGridProps) {
  const list = stats.filter((s) => s.value?.trim() || s.label?.trim())
  const hasHeader = Boolean(
    eyebrow?.trim() || title?.trim() || description?.trim(),
  )

  if (list.length === 0 && !hasHeader) {
    return null
  }

  return (
    <section className="w-full bg-white py-10 md:py-14">
      <Container className="flex flex-col items-center">
        <SectionFigmaBlockHeader
          eyebrow={eyebrow}
          title={title}
          description={description}
          titleSize="module"
        />
        {list.length > 0 ? (
          <FigmaStatsGrid stats={list} columns={columns} />
        ) : null}
      </Container>
    </section>
  )
}
