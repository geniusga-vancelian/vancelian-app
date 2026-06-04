import { PortalBundleInvestScreen } from '@/components/portal/bundles/PortalBundleInvestScreen'

type Props = {
  params: { portfolioId: string }
}

export default function PortalBundleInvestPage({ params }: Props) {
  return <PortalBundleInvestScreen portfolioId={params.portfolioId} />
}
