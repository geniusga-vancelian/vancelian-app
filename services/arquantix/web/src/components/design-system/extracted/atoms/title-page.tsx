import { cn } from '@/lib/utils'

export type TitlepageAlign = 'left' | 'center' | 'right'

export interface TitlepageProps {
  children: React.ReactNode
  align?: TitlepageAlign
  /** Couleur du texte (ex. `#000000` / `white`). */
  color?: string
  className?: string
  as?: 'h1' | 'h2' | 'h3'
  id?: string
}

const ALIGN_OUTER: Record<TitlepageAlign, string> = {
  left: 'items-start',
  center: 'items-center',
  right: 'items-end',
}

const ALIGN_INNER: Record<TitlepageAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

/**
 * **Titlepage** — atome DS (Figma « Page Title ») : Avenir Heavy 800, 56px (max responsive),
 * interligne 100 %, interlettrage −2 %, centré par défaut.
 */
export function Titlepage({
  children,
  align = 'center',
  color,
  className,
  as: Comp = 'h1',
  id,
}: TitlepageProps) {
  return (
    <div
      className={cn('flex w-full flex-col justify-center not-italic', ALIGN_OUTER[align])}
      data-name="Titlepage"
    >
      <Comp
        id={id}
        className={cn(
          "m-0 block w-full font-['Avenir:Heavy',sans-serif] font-extrabold text-[48px] leading-none tracking-[-0.02em] md:text-[clamp(3rem,5vw,56px)]",
          ALIGN_INNER[align],
          className,
        )}
        style={color ? { color } : undefined}
      >
        {children}
      </Comp>
    </div>
  )
}
