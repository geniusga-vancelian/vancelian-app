import { cn } from '@/lib/utils'

export type PortalImageMosaicItem = {
  url: string
  alt?: string | null
}

type Props = {
  items: PortalImageMosaicItem[]
  className?: string
}

/** Colonnes grille article (`art-prose__grid`) selon le nombre de photos. */
export function portalImageMosaicCols(count: number): 1 | 2 | 3 {
  if (count <= 1) return 1
  if (count === 2) return 2
  return 3
}

/** Mosaïque DS article — desktop / espace suffisant (2 ou 3 colonnes). */
export function PortalImageMosaic({ items, className }: Props) {
  const photos = items.filter((item) => item.url.trim())
  if (!photos.length) return null

  const cols = portalImageMosaicCols(photos.length)

  return (
    <div className={cn('art-prose__grid', `art-prose__grid--c${cols}`, className)}>
      {photos.map((item, i) => (
        <span
          key={`${item.url}-${i}`}
          className="art-prose__grid-cell"
          style={{ backgroundImage: `url('${item.url}')` }}
          role="img"
          aria-label={item.alt?.trim() || undefined}
        />
      ))}
    </div>
  )
}
