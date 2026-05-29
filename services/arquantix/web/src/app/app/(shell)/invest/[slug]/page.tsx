import { notFound } from 'next/navigation'
import { getExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { PortalOfferDetailScreen } from '@/components/portal/invest/PortalOfferDetailScreen'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

type Props = {
  params: Promise<{ slug: string }>
}

/** Détail offre exclusive portail — handoff Offre.html. */
export default async function PortalInvestOfferPage({ params }: Props) {
  const { slug } = await params
  const payload = await getExclusiveOfferVaultPayload(slug, PORTAL_CONTENT_LOCALE)
  if (!payload) {
    notFound()
  }

  return <PortalOfferDetailScreen payload={payload} />
}
