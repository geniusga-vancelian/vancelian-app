'use client'

import { PortalInstrumentDetailScreen } from '@/components/portal/markets/PortalInstrumentDetailScreen'

type Props = {
  params: { ticker: string }
}

export default function PortalInstrumentDetailPage({ params }: Props) {
  return <PortalInstrumentDetailScreen ticker={params.ticker} />
}
