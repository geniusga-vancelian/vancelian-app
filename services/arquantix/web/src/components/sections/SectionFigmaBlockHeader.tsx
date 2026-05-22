import { cn } from '@/lib/utils'
import {
  VSectionHeader,
} from '@/components/design-system/vancelian'
import { arquantixContentTextMaxWidthClass } from '@/lib/design/contentMaxWidth'
import { parseEditorialTitle } from '@/lib/cms/parseEditorialTitle'

function resolveEditorialTitle(raw?: string) {
  const t = raw?.trim()
  if (!t) return undefined
  return parseEditorialTitle(t.replace(/\n+/g, '<br />'))
}

/**
 * En-tête optionnel (surtitre + titre + description) pour sections Figma CMS.
 * Délègue à {@link VSectionHeader} (pattern DS standard).
 *
 * `titleSize="small"` (défaut Figma legacy) → mappé vers `module` Vancelian.
 * `titleSize="module"` → mappé vers `page` Vancelian (gros titre de section).
 */
export function SectionFigmaBlockHeader({
  eyebrow,
  title,
  description,
  className,
  titleSize = 'small',
}: {
  eyebrow?: string
  title?: string
  description?: string
  /** Fusionné en dernier (ex. `mb-16` pour espacement Figma sous le bloc). */
  className?: string
  /** `small` = titre 28–40px (défaut). `module` = titre de section 40–56px. */
  titleSize?: 'module' | 'small'
}) {
  const e = eyebrow?.trim()
  const t = resolveEditorialTitle(title)
  const d = description?.trim()
  if (!e && !t && !d) return null

  // Mapping legacy → DS Vancelian
  const vSize = titleSize === 'module' ? 'page' : 'module'

  return (
    <div
      className={cn(
        'mx-auto mb-12 flex w-full justify-center px-4',
        arquantixContentTextMaxWidthClass,
        className,
      )}
    >
      <VSectionHeader
        eyebrow={e}
        title={t}
        description={d}
        titleAs="h2"
        titleSize={vSize}
        align="center"
        maxWidth={720}
      />
    </div>
  )
}
