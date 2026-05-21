'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Logo, type LogoColor, type LogoLockup } from '@/components/ui/Logo'

export type SiteBrandLogo = {
  logoUrl: string | null
  logoAlt: string | null
}

type BrandLogoProps = {
  brand?: SiteBrandLogo | null
  lockup?: LogoLockup
  color?: LogoColor
  alt?: string
  className?: string
  style?: React.CSSProperties
}

/**
 * Logo Vancelian — priorité au média CMS (footer global), repli sur les SVG statiques du DS.
 */
export function BrandLogo({
  brand: brandProp,
  lockup = 'horizontal',
  color = 'black',
  alt = 'Vancelian',
  className,
  style,
}: BrandLogoProps) {
  const [brand, setBrand] = React.useState<SiteBrandLogo | null>(brandProp ?? null)

  React.useEffect(() => {
    if (brandProp) {
      setBrand(brandProp)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/site/brand-logo', { cache: 'no-store' })
        if (!res.ok) return
        const data = (await res.json()) as SiteBrandLogo
        if (!cancelled) setBrand(data)
      } catch {
        // repli SVG statique
      }
    })()
    return () => {
      cancelled = true
    }
  }, [brandProp])

  const cmsUrl = brand?.logoUrl?.trim()
  if (cmsUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- URL CMS (proxy / R2)
      <img
        src={cmsUrl}
        alt={brand?.logoAlt?.trim() || alt}
        className={cn('block max-h-full w-auto', className)}
        style={style}
      />
    )
  }

  return <Logo lockup={lockup} color={color} alt={alt} className={className} style={style} />
}
