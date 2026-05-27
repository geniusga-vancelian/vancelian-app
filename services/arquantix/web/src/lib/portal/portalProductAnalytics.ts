/** Lightweight product analytics — stdout JSON today, provider hook later. */
export function trackPortalProductEvent(
  event: string,
  properties: Record<string, unknown>,
): void {
  if (typeof window === 'undefined') return

  const payload = {
    ts: new Date().toISOString(),
    service: 'arquantix-web',
    component: 'portal_product',
    event,
    ...properties,
  }

  console.info('[portal:product]', JSON.stringify(payload))
}

export function trackLombardCtaClicked(args: {
  asset: string
  chainId: number
  source: 'wallet_asset_detail'
  cta: 'borrow_usdc' | 'deposit_to_borrow'
}): void {
  trackPortalProductEvent('lombard_cta_clicked', {
    asset: args.asset,
    chainId: args.chainId,
    source: args.source,
    cta: args.cta,
  })
}
