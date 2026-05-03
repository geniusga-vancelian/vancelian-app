import { cn } from '@/lib/utils'
import { figmaDsCategoryPillContainerClassName } from '../tokens/typography'
import { Label } from './label'

export type CategoryPillProps = {
  /** Libellé au style atome **Label** (uppercase côté CSS). */
  label: string
  /** Pastille de couleur (ex. `bg-orange-500`). Si absent, seul le texte est affiché (ex. segment éditorial). */
  dotClassName?: string
  className?: string
}

/**
 * Atome DS — **pill catégorie** (point + libellé) aligné Figma :
 * conteneur `figmaDsCategoryPillContainerClassName` + atome **Label** (texte noir).
 */
export function CategoryPill({ label, dotClassName, className }: CategoryPillProps) {
  return (
    <span className={cn(figmaDsCategoryPillContainerClassName, className)}>
      {dotClassName ? (
        <span
          className={cn('size-[7px] shrink-0 rounded-full', dotClassName)}
          aria-hidden
        />
      ) : null}
      <Label className="text-black">{label}</Label>
    </span>
  )
}

/** Jeu de couleurs par défaut pour la pastille (rotation sur plusieurs catégories). */
export const categoryPillDotPalette = [
  'bg-orange-500',
  'bg-emerald-500',
  'bg-sky-500',
  'bg-violet-500',
] as const
