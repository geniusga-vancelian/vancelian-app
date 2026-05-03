import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { ExclusiveOfferVaultDetail } from '@/components/exclusive-offer/ExclusiveOfferVaultDetail'

export type SectionExclusiveOfferVaultProps = {
  exclusiveOfferVaultPayload?: ExclusiveOfferVaultPayload | null
}

/**
 * Slot gabarit CMS : rend le corps Vault Builder pour la page `/projects/[slug]` courante.
 */
export function SectionExclusiveOfferVault({
  exclusiveOfferVaultPayload,
}: SectionExclusiveOfferVaultProps) {
  if (!exclusiveOfferVaultPayload) {
    return null
  }
  return <ExclusiveOfferVaultDetail payload={exclusiveOfferVaultPayload} />
}
