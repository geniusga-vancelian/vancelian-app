import { FigmaTestimonialCard } from '@/components/design-system/extracted'
import { arquantixContentTextBlockClass } from '@/lib/design/contentMaxWidth'
import { Container } from '@/components/ui/Container'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { cn } from '@/lib/utils'

export interface FigmaTestimonialItem {
  author: string
  role: string
  content: string
  /** @deprecated URL directe — préférer avatarMediaUrl */
  avatar?: string
  avatarMediaId?: string
  /** Injecté par getPageSections depuis avatarMediaId */
  avatarMediaUrl?: string
  backgroundColor?: string
}

export interface SectionFigmaTestimonialCardsProps {
  eyebrow?: string
  title?: string
  description?: string
  /** 1 = une carte par ligne ; 2 = grille 2 colonnes (à partir du breakpoint `md`). */
  cardsPerRow?: 1 | 2
  items?: FigmaTestimonialItem[]
}

export function SectionFigmaTestimonialCards({
  eyebrow,
  title,
  description,
  cardsPerRow = 1,
  items = [],
}: SectionFigmaTestimonialCardsProps) {
  const list = items.filter((i) => i.content?.trim())
  const hasHeader = Boolean(
    eyebrow?.trim() || title?.trim() || description?.trim(),
  )

  if (list.length === 0 && !hasHeader) {
    return null
  }

  return (
    <section className="w-full bg-white pt-16 pb-32">
      <Container>
        <SectionFigmaBlockHeader
          eyebrow={eyebrow}
          title={title}
          description={description}
          titleSize="module"
          className="mb-16"
        />
        {list.length > 0 ? (
          <div
            className={cn(
              'w-full',
              cardsPerRow === 2
                ? 'grid grid-cols-1 gap-6 md:grid-cols-2 md:items-stretch'
                : 'flex flex-col gap-6',
            )}
          >
            {list.map((item, index) => {
              const avatarSrc =
                (typeof item.avatarMediaUrl === 'string' && item.avatarMediaUrl.trim()
                  ? item.avatarMediaUrl.trim()
                  : undefined) ||
                (typeof item.avatar === 'string' && item.avatar.trim()
                  ? item.avatar.trim()
                  : undefined)
              return (
                <div
                  key={`${item.author}-${index}`}
                  className={cn(
                    cardsPerRow === 2 ? 'h-full min-w-0' : arquantixContentTextBlockClass,
                  )}
                >
                  <FigmaTestimonialCard
                    author={item.author}
                    role={item.role}
                    content={item.content}
                    avatar={avatarSrc}
                    backgroundColor={item.backgroundColor ?? '#f4f4f4'}
                    className={cardsPerRow === 2 ? 'h-full' : undefined}
                  />
                </div>
              )
            })}
          </div>
        ) : null}
      </Container>
    </section>
  )
}
