import { notFound } from 'next/navigation'

import { PortalVaultInvestScreen } from '@/components/portal/invest/PortalVaultInvestScreen'
import { getExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

type Props = {
  params: Promise<{ slug: string }>
}

/** Investissement offre exclusive — handoff InvestFlow dans `.placer-invest__panel`. */
export default async function PortalVaultInvestPage({ params }: Props) {
  const { slug } = await params
  const payload = await getExclusiveOfferVaultPayload(slug, PORTAL_CONTENT_LOCALE)
  if (!payload) {
    notFound()
  }

  return <PortalVaultInvestScreen payload={payload} />
}
