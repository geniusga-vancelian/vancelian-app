'use client'

import { useScrollSectionFade } from '@/hooks/useScrollSectionFade'

/** Active les effets scroll globaux (fade sections) sur le site public. */
export function ScrollMotionEffects() {
  useScrollSectionFade(true)
  return null
}
