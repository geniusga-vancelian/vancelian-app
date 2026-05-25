'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { Button } from '@/components/ui/button'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  chainLabel: string
  supportedChainKeys: string[]
  onBack?: () => void
}

export function PortalSwapUnsupportedNotice({
  chainLabel,
  supportedChainKeys,
  onBack,
}: Props) {
  const supportedLabels = supportedChainKeys
    .map((key) => SWAP_CHAIN_LABELS[key] ?? key)
    .join(', ')

  return (
    <PortalSwapFlowShell title="Swap" onBack={onBack}>
      <article className="mx-auto max-w-lg rounded-v-card border border-v-border bg-v-card px-5 py-6 text-center shadow-v-subtle">
        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">
          Échange indisponible sur {chainLabel}
        </p>
        <p className="m-0 mt-2 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          {supportedChainKeys.length > 0
            ? `LI.FI n’est pas activé sur ${chainLabel} pour le moment. Réseaux disponibles : ${supportedLabels}.`
            : `LI.FI n’est pas disponible sur ${chainLabel}. Les échanges EVM (Base, Ethereum…) seront proposés dès qu’ils seront activés côté backend.`}
        </p>
        <p className="m-0 mt-2 font-ui text-[13px] text-v-fg-muted">
          Vous pouvez changer de réseau dans la navbar ou revenir à votre wallet crypto.
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Button type="button" variant="outline" className="rounded-full" asChild>
            <PortalNavLink href={PORTAL_ROUTES.cryptoWallet}>Retour au wallet</PortalNavLink>
          </Button>
        </div>
      </article>
    </PortalSwapFlowShell>
  )
}
