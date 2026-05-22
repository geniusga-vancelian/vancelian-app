import { VHero } from '@/components/design-system/vancelian/VHero'

export interface SectionFigmaSimpleHeroProps {
  title?: string
  description?: string
  /** Couleur de fond CMS — détermine le ton (clair / sombre). */
  backgroundColor?: string
  /** Couleur de texte CMS — utilisée pour décider du tone du hero. */
  textColor?: string
}

/**
 * Hero simple texte (sans image) — Vancelian Design System.
 *
 * Délègue à {@link VHero} en variant `secondary` quand fond clair,
 * `light` sinon. Conserve l'API CMS historique (`backgroundColor`, `textColor`).
 *
 * Note : la couleur exacte CMS est appliquée via wrapper `<section>` pour
 * conserver la liberté éditoriale du CMS, mais la doctrine recommande
 * d'utiliser les tons Vancelian (`--v-bg`, `--v-dark-bg`).
 */
export function SectionFigmaSimpleHero({
  title = '',
  description = '',
  backgroundColor = '#F7F7F4',
  textColor = '#1A1815',
}: SectionFigmaSimpleHeroProps) {
  if (!title.trim() && !description.trim()) return null

  // Heuristique : texte clair → ton inverse (variant dark sans image)
  const isDarkText = ['#000', '#1a1815', '#1d1d1f', '#272727']
    .some((d) => textColor?.toLowerCase().startsWith(d))
  const variant: 'light' | 'dark' | 'secondary' = isDarkText ? 'secondary' : 'dark'

  return (
    <div style={{ backgroundColor }}>
      <VHero
        variant={variant}
        title={title}
        subtitle={description}
        minHeight="auto"
      />
    </div>
  )
}
