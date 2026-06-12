'use client'

import { Zap } from 'lucide-react'

import {
  PortalSectionTitle,
  PortalSettingsCard,
  PortalSettingsRow,
} from '@/components/portal/profile/PortalProfileUi'
import { usePortalWalletDelegation } from '@/lib/portal/usePortalWalletDelegation'
import { cn } from '@/lib/utils'

/**
 * Activation de l'exécution automatique : délègue (one-time) le wallet embedded
 * de l'utilisateur au signer serveur Vancelian (Privy Session Signers).
 * Masquée si la fonctionnalité n'est pas configurée côté app.
 */
export function PortalProfileDelegationSection() {
  const { isConfigured, isDelegated, canDelegate, isDelegating, error, delegate } =
    usePortalWalletDelegation()

  if (!isConfigured) return null

  const subtitle = isDelegated
    ? 'Vancelian peut exécuter vos ordres automatiquement.'
    : 'Autorisez Vancelian à exécuter vos ordres sans signer à chaque fois.'

  return (
    <section className="flex flex-col gap-3">
      <PortalSectionTitle>Exécution automatique</PortalSectionTitle>
      <PortalSettingsCard>
        <PortalSettingsRow
          title="Trading automatique"
          subtitle={subtitle}
          leading={<Zap className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
          trailing={
            <button
              type="button"
              role="switch"
              aria-checked={isDelegated}
              aria-label="Activer l'exécution automatique"
              disabled={isDelegated || isDelegating || !canDelegate}
              onClick={() => {
                if (canDelegate) void delegate()
              }}
              className={cn(
                'relative h-7 w-12 shrink-0 rounded-v-pill border-0 transition-colors duration-v-fast disabled:cursor-default',
                isDelegated ? 'bg-v-fg' : 'bg-v-fg-20',
                isDelegating && 'opacity-60',
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-v-subtle transition-transform duration-v-fast',
                  isDelegated ? 'translate-x-[22px]' : 'translate-x-0.5',
                )}
              />
            </button>
          }
        />
      </PortalSettingsCard>
      {error ? <p className="m-0 px-1 font-ui text-[13px] text-v-error">{error}</p> : null}
      <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
        Vos fonds restent en auto-conservation. Vous pouvez révoquer cette autorisation à tout
        moment.
      </p>
    </section>
  )
}
