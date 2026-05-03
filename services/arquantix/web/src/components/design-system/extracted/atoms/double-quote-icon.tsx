import { useId } from 'react'
import { cn } from '@/lib/utils'

type DoubleQuoteIconProps = {
  className?: string
  title?: string
}

/**
 * Atome DS - Double Quote icon
 * Source: `Vector.svg` (simple quote) dupliqué ; 2ᵉ forme décalée pour ~2px entre les deux.
 */
export function DoubleQuoteIcon({ className, title }: DoubleQuoteIconProps) {
  const gradientId = useId()

  /* Écart horizontal entre les deux guillemets : ~2px à l’échelle d’affichage (viewBox 1 unité ≈ 1px en largeur). */
  const secondTranslateX = -5.75

  return (
    <svg
      viewBox="0 0 28.5 21"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('h-[21px] w-[28.5px]', className)}
      role={title ? 'img' : 'presentation'}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      <path
        d="M1.80488 0V9.79597H5.805C5.805 9.79597 5.4885 15.438 0 18.079L1.24275 21C1.24275 21 1.614 20.9631 2.23238 20.8361C9.13688 19.4186 14.0625 13.5187 14.0625 6.70852V0H1.80488Z"
        fill={`url(#${gradientId})`}
      />
      <path
        transform={`translate(${secondTranslateX} 0)`}
        d="M21.8049 0V9.79597H25.805C25.805 9.79597 25.4885 15.438 20 18.079L21.2427 21C21.2427 21 21.614 20.9631 22.2324 20.8361C29.1369 19.4186 34.0625 13.5187 34.0625 6.70852V0H21.8049Z"
        fill={`url(#${gradientId})`}
      />
      <defs>
        <linearGradient id={gradientId} x1="17.03125" y1="0" x2="17.03125" y2="21" gradientUnits="userSpaceOnUse">
          <stop stopColor="#E885D0" />
          <stop offset="1" stopColor="#FFB84D" />
        </linearGradient>
      </defs>
    </svg>
  )
}
