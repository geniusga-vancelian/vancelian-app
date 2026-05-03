import { SectionTitle } from '@/components/design-system/extracted'
import { arquantixContentTextMaxWidthClass } from '@/lib/design/contentMaxWidth'
import { cn } from '@/lib/utils'

/**
 * Surtitre aligné sur la homepage (ProjetGallery) : filets verticaux gauche/droite, pas de cadre complet.
 */
function HomepageStyleSectionEyebrow({ text }: { text: string }) {
  return (
    <div className="relative flex shrink-0 content-stretch items-center justify-center rounded-[2px] px-[4px] py-[2px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-[2px] border-solid border-[#62656e] border-l border-r"
      />
      <p className="relative whitespace-nowrap font-['Avenir:Heavy',sans-serif] text-[14px] uppercase leading-none not-italic text-[#62656e]">
        {text}
      </p>
    </div>
  )
}

/**
 * En-tête optionnel (surtitre + titre + description) pour sections Figma CMS — aligné ProjetGallery (homepage).
 * Par défaut le titre utilise l’atome **Title small** (24px Heavy) ; les grosses bandeaux (stats, témoignages) peuvent repasser en `titleSize="module"` (40px).
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
  /** `small` = Figma **Title small** (24px) — défaut. `module` = titre de section 40px (blocs page large). */
  titleSize?: 'module' | 'small'
}) {
  const e = eyebrow?.trim()
  const t = title?.trim()
  const d = description?.trim()
  if (!e && !t && !d) {
    return null
  }

  const titleColor = '#1d1d1f'

  return (
    <div
      className={cn(
        'mx-auto mb-10 flex w-full flex-col items-center gap-6 px-4 text-center md:mb-12',
        arquantixContentTextMaxWidthClass,
        className,
      )}
    >
      {(e || t) ? (
        <div className="flex w-full flex-col items-center gap-[10px]">
          {e ? <HomepageStyleSectionEyebrow text={e} /> : null}
          {t ? (
            <SectionTitle
              size={titleSize}
              align="center"
              color={titleColor}
            >
              {t}
            </SectionTitle>
          ) : null}
        </div>
      ) : null}
      {d ? (
        <p className="w-full font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black">
          {d}
        </p>
      ) : null}
    </div>
  )
}
