'use client'

import { Zap } from 'lucide-react'

import {
  PortalSectionTitle,
  PortalSettingsCard,
  PortalSettingsRow,
} from '@/components/portal/profile/PortalProfileUi'
import { getPrivyAuthorizationQuorumId } from '@/lib/portal/privyConfig'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/**
 * Entrée "Exécution automatique" du profil.
 *
 * L'activation/désactivation réelle (Privy Session Signers) exige une session SDK
 * Privy active, indisponible sur le profil (doctrine "Privy ≠ navigation"). On
 * renvoie donc vers la page dédiée `/app/wallet/auto-trading` (sous Web3 boundary)
 * où la délégation fonctionne réellement. Masquée si non configurée côté app.
 */
export function PortalProfileDelegationSection() {
  const isConfigured = Boolean(getPrivyAuthorizationQuorumId())
  if (!isConfigured) return null

  return (
    <section className="flex flex-col gap-3">
      <PortalSectionTitle>Exécution automatique</PortalSectionTitle>
      <PortalSettingsCard>
        <PortalSettingsRow
          title="Trading automatique"
          subtitle="Autorisez Vancelian à exécuter vos ordres sans signer à chaque fois."
          href={PORTAL_ROUTES.walletAutoTrading}
          leading={<Zap className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
        />
      </PortalSettingsCard>
      <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
        Vos fonds restent en auto-conservation. Vous pouvez révoquer cette autorisation à tout
        moment.
      </p>
    </section>
  )
}
