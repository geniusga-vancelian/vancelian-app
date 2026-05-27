'use client'

import { PortalCryptoBundleDetailScreen } from '@/components/portal/bundles/PortalCryptoBundleDetailScreen'

type Props = {
  params: { productCode: string }
}

export default function PortalCryptoBundleProductPage({ params }: Props) {
  return <PortalCryptoBundleDetailScreen productCode={params.productCode} />
}
