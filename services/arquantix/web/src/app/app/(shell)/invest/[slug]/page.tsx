import { notFound } from 'next/navigation'
import { getExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { ExclusiveOfferVaultDetail } from '@/components/exclusive-offer/ExclusiveOfferVaultDetail'

type Props = {
  params: Promise<{ slug: string }>
}

/** Détail offre exclusive dans la webapp — même rendu vault DS que le site public. */
export default async function PortalInvestOfferPage({ params }: Props) {
  const { slug } = await params
  const payload = await getExclusiveOfferVaultPayload(slug, 'fr')
  if (!payload) {
    notFound()
  }

  return <ExclusiveOfferVaultDetail payload={payload} />
}
