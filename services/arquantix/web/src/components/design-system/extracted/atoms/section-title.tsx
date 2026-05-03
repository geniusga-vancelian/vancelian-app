import { cn } from '@/lib/utils'

export type SectionTitleAlign = 'left' | 'center' | 'right'

/**
 * Variantes de taille du titre de section.
 * `module` = spec atome « Section title » (40px, lh 110 %, tracking −1 %).
 * `title` = spec Figma **Title** (32px, lh 110 %, tracking −1 %, Heavy 800) — ex. titres d’étape How it works.
 */
export type SectionTitleSize = 'module' | 'large' | 'small' | 'title'

export interface SectionTitleProps {
  children: React.ReactNode
  /**
   * `module` : titre de module CMS — Avenir Heavy 800, 40px, interligne 110 %, tracking −1 %, centré par défaut.
   * `title` : **Title** Figma — Heavy 800, 32px, interligne 110 %, tracking −1 %.
   * `large` : 56px · `small` : **Title small** Figma — Heavy 800, 24px, interligne 110 %, tracking −1 %.
   * @deprecated `medium` → équivalent à `module`.
   */
  size?: SectionTitleSize | 'medium'
  align?: SectionTitleAlign
  color?: string
  className?: string
  /** Ancre DOM (ex. blend nav sur hero blog / article). */
  id?: string
  /** Sémantique du titre (SEO / a11y). */
  as?: 'h1' | 'h2' | 'h3'
}

const SIZE_CLASS: Record<SectionTitleSize, string> = {
  module:
    "font-['Avenir:Heavy',sans-serif] font-extrabold text-[40px] leading-[1.1] tracking-[-0.01em]",
  title:
    "font-['Avenir:Heavy',sans-serif] font-extrabold text-[32px] leading-[1.1] tracking-[-0.01em]",
  large:
    "font-['Avenir:Heavy',sans-serif] font-extrabold text-[56px] leading-[1.1] tracking-[-0.01em]",
  small:
    "font-['Avenir:Heavy',sans-serif] font-extrabold text-[24px] leading-[1.1] tracking-[-0.01em]",
}

/** Token DS explicite : Title small (24px, lh 110%, tracking -1%, Heavy 800). */
export const figmaDsTitleSmallClassName =
  "font-['Avenir:Heavy',sans-serif] font-extrabold text-[24px] leading-[1.1] tracking-[-0.01em]" as const

const ALIGN_OUTER: Record<SectionTitleAlign, string> = {
  left: 'items-start',
  center: 'items-center',
  right: 'items-end',
}

const ALIGN_INNER: Record<SectionTitleAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

/**
 * **Section title** — atome DS (Figma) : Avenir Heavy 800, 40px, interligne 110 %, interlettrage −1 %,
 * alignement horizontal centré par défaut, contenu centré verticalement dans le bloc titre.
 */
export function SectionTitle({
  children,
  size = 'module',
  align = 'center',
  color = '#1d1d1f',
  className,
  id,
  as: Comp = 'h2',
}: SectionTitleProps) {
  const resolved: SectionTitleSize = size === 'medium' ? 'module' : size

  return (
    <div
      className={cn(
        'flex w-full flex-col justify-center not-italic',
        ALIGN_OUTER[align],
      )}
      data-name="Section title"
    >
      <Comp
        id={id}
        className={cn('m-0 block w-full', SIZE_CLASS[resolved], ALIGN_INNER[align], className)}
        style={{ color }}
      >
        {children}
      </Comp>
    </div>
  )
}

/** @deprecated Préférer l’atome {@link SectionTitle} (« Section title »). */
export const FigmaSectionTitle = SectionTitle
