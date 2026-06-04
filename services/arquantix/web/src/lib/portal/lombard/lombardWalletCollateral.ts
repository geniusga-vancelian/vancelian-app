import { parseLombardHumanAmountToRaw } from '@/lib/portal/lombard/lombardFormat'

/** Solde garantie affiché dans le hub wallet (aligné swap spendable). */
export function resolvePortalCollateralBalanceHuman(args: {
  balance?: number | null
  availableBalance?: number | null
  onChainBalance?: number | null
}): number {
  const onChain = args.onChainBalance
  if (onChain != null && Number.isFinite(onChain) && onChain > 0) return onChain
  const available = args.availableBalance
  if (available != null && Number.isFinite(available) && available > 0) return available
  const balance = args.balance
  if (balance != null && Number.isFinite(balance) && balance > 0) return balance
  return 0
}

/**
 * Garantie wallet effective pour capacité / devis Morpho.
 * Le hub peut afficher un solde plateforme alors que `balanceOf` RPC est encore à 0 ;
 * on retient le max pour ne pas bloquer l’emprunt quand les fonds sont visibles côté portail.
 */
export function resolveEffectiveWalletCollateralRaw(args: {
  onChainRaw: bigint
  portalBalanceHuman?: string | null
  decimals: number
}): bigint {
  const portalHuman = args.portalBalanceHuman?.trim()
  if (!portalHuman) return args.onChainRaw
  try {
    const portalRaw = parseLombardHumanAmountToRaw(portalHuman, args.decimals)
    return portalRaw > args.onChainRaw ? portalRaw : args.onChainRaw
  } catch {
    return args.onChainRaw
  }
}
