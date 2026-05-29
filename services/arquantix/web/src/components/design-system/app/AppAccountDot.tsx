import type { ReactNode } from 'react'
import { KalaiIcon, type KalaiIconProps } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppAccountDotVariant =
  | 'dark'
  | 'terra'
  | 'green'
  | 'blue'
  | 'warm'
  | 'safran'
  | 'custom'

type Props = {
  size?: number
  variant?: AppAccountDotVariant
  /** Initiales ou nom d’icône Kalai */
  glyph?: string | { name: NonNullable<KalaiIconProps['name']> }
  glyphSize?: number
  customBg?: string
  imageUrl?: string
  imageAlt?: string
  className?: string
  children?: ReactNode
}

/** Pastille compte — DS `.avt` / `.avt--*` (handoff primitives.jsx). */
export function AppAccountDot({
  size = 40,
  variant = 'dark',
  glyph,
  glyphSize,
  customBg,
  imageUrl,
  imageAlt = '',
  className,
  children,
}: Props) {
  const isKalaiIcon =
    glyph != null && typeof glyph === 'object' && 'name' in glyph
  const variantClass =
    variant !== 'custom' ? `avt--${variant}` : ''

  return (
    <span
      className={cn('avt', variantClass, className)}
      style={{
        ['--avt-size' as string]: `${size}px`,
        ...(customBg ? { background: customBg, color: '#fff' } : {}),
      }}
    >
      {children}
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt={imageAlt} className="h-full w-full object-cover" />
      ) : isKalaiIcon ? (
        <KalaiIcon
          name={glyph.name}
          size={(glyphSize === 16 || glyphSize === 20 || glyphSize === 24 || glyphSize === 32
            ? glyphSize
            : 20) as KalaiIconProps['size']}
          className="avt__ic"
        />
      ) : glyph ? (
        <span
          className="font-ui font-semibold leading-none"
          style={{ fontSize: size * 0.42 }}
        >
          {glyph}
        </span>
      ) : null}
    </span>
  )
}
