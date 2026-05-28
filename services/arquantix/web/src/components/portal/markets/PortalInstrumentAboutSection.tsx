'use client'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { instrumentAboutBlurb } from '@/lib/portal/instrumentDetailFormat'

type Props = {
  name: string
  ticker: string
}

/** Bloc à propos — handoff `.ast-prose`. */
export function PortalInstrumentAboutSection({ name, ticker }: Props) {
  return (
    <section>
      <AppSectionHeader title="À propos" size="md" />
      <p className="ast-prose">{instrumentAboutBlurb(name, ticker)}</p>
    </section>
  )
}
