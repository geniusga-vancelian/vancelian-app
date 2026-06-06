import { notFound, redirect } from 'next/navigation'

import { getExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { PortalVaultInvestScreen } from '@/components/portal/invest/PortalVaultInvestScreen'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import {
  parsePortalVaultFlowMode,
  resolvePortalVaultEngineInvestRoute,
} from '@/lib/portal/portalRouting'

type Props = {
  params: Promise<{ slug: string }>
  searchParams: Promise<{ mode?: string }>
}

/** Investissement offre / vault catalogue — redirige vers le flux DeFi si moteur VAULT_ENGINE. */
export default async function PortalVaultInvestPage({ params, searchParams }: Props) {
  const { slug } = await params
  const query = await searchParams
  const mode = parsePortalVaultFlowMode(query.mode ?? null)
  const payload = await getExclusiveOfferVaultPayload(slug, PORTAL_CONTENT_LOCALE)
  if (!payload) {
    notFound()
  }

  if (payload.vaultEngine?.vault_address && payload.vaultEngine.integration_mode) {
    redirect(resolvePortalVaultEngineInvestRoute(payload.vaultEngine, slug, mode))
  }

  return <PortalVaultInvestScreen payload={payload} />
}
