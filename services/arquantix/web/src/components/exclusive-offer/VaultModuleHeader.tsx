'use client'

import { VSectionHeader } from '@/components/design-system/vancelian/VSectionHeader'
import { cn } from '@/lib/utils'

type Props = {
  eyebrow?: string
  title?: string
  description?: string
  align?: 'left' | 'center'
  className?: string
}

/** En-tête vault unifié — délègue au {@link VSectionHeader} DS site. */
export function VaultModuleHeader({
  eyebrow,
  title,
  description,
  align = 'center',
  className,
}: Props) {
  const e = eyebrow?.trim()
  const t = title?.trim()
  const d = description?.trim()
  if (!e && !t && !d) return null

  return (
    <VSectionHeader
      eyebrow={e || undefined}
      title={t || undefined}
      description={d || undefined}
      titleAs="h2"
      titleSize="module"
      align={align}
      className={cn('mb-8 md:mb-10', className)}
    />
  )
}
