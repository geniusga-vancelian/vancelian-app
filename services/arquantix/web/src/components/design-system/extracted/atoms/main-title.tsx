import { cn } from '@/lib/utils'

export type MainTitleAlign = 'left' | 'center' | 'right'

/** Classes du bloc titre (hero homepage) — à réutiliser p.ex. sur `GradientHeading`. */
export const mainTitleTypographyClassName =
  "font-ui font-medium font-medium text-[48px] leading-none tracking-[-0.02em] not-italic md:text-[clamp(3rem,6vw,72px)]"

const ALIGN_OUTER: Record<MainTitleAlign, string> = {
  left: 'items-start',
  center: 'items-center',
  right: 'items-end',
}

const ALIGN_INNER: Record<MainTitleAlign, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

export interface MainTitleProps {
  children: React.ReactNode
  align?: MainTitleAlign
  color?: string
  className?: string
  as?: 'h1' | 'h2' | 'div'
  id?: string
}

/**
 * **Main title** — atome DS (Figma) : Avenir Medium 500, 72px max (clamp), interligne 100 %,
 * interlettrage −2 %, centré par défaut (hero homepage).
 */
export function MainTitle({
  children,
  align = 'center',
  color = '#000000',
  className,
  as: Comp = 'h1',
  id,
}: MainTitleProps) {
  return (
    <div
      className={cn(
        'flex w-full flex-col justify-center not-italic',
        ALIGN_OUTER[align],
      )}
      data-name="Main title"
    >
      <Comp
        id={id}
        className={cn('m-0 block w-full', mainTitleTypographyClassName, ALIGN_INNER[align], className)}
        style={{ color }}
      >
        {children}
      </Comp>
    </div>
  )
}
