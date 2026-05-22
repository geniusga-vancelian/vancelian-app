import { Container } from '@/components/ui/Container'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { cn } from '@/lib/utils'
import { VTcard } from '@/components/design-system/vancelian'

export interface FigmaTestimonialItem {
  author: string
  role: string
  content: string
  /** @deprecated URL directe — préférer avatarMediaUrl */
  avatar?: string
  avatarMediaId?: string
  /** Injecté par getPageSections depuis avatarMediaId */
  avatarMediaUrl?: string
  /** @deprecated Couleur de fond ignorée — le DS Vancelian utilise un fond unifié. */
  backgroundColor?: string
}

export interface SectionFigmaTestimonialCardsProps {
  eyebrow?: string
  title?: string
  description?: string
  /** 1 = une carte par ligne ; 2 = grille 2 colonnes (DS Vancelian par défaut). */
  cardsPerRow?: 1 | 2
  items?: FigmaTestimonialItem[]
}

/**
 * Cartes témoignages CMS Figma — Vancelian Design System.
 *
 * Délègue à {@link VTcard} (pattern `tcard` du pack handoff).
 * Le DS recommande 2 colonnes desktop, on respecte donc `cardsPerRow` par
 * compatibilité CMS (1 = pile, 2 = grille).
 */
export function SectionFigmaTestimonialCards({
  eyebrow,
  title,
  description,
  cardsPerRow = 2,
  items = [],
}: SectionFigmaTestimonialCardsProps) {
  const list = items.filter((i) => i.content?.trim())
  const hasHeader = Boolean(
    eyebrow?.trim() || title?.trim() || description?.trim(),
  )

  if (list.length === 0 && !hasHeader) return null

  return (
    <section className="w-full bg-v-bg py-24 lg:py-32">
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
              'w-full gap-6',
              cardsPerRow === 2
                ? 'grid grid-cols-1 md:grid-cols-2 md:items-stretch'
                : 'flex flex-col items-stretch max-w-[680px] mx-auto',
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
                <VTcard
                  key={`${item.author}-${index}`}
                  quote={item.content}
                  authorName={item.author}
                  authorRole={item.role}
                  avatarUrl={avatarSrc}
                  rating={0}
                />
              )
            })}
          </div>
        ) : null}
      </Container>
    </section>
  )
}
