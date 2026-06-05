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
 * on retient le solde portail uniquement dans ce cas (RPC en retard).
 * Si `balanceOf` est déjà > 0, on ne gonfle jamais avec le portail — sinon simulation
 * open_loan revert (ERC20 transfer amount exceeds balance).
 */
export function resolveEffectiveWalletCollateralRaw(args: {
  onChainRaw: bigint
  portalBalanceHuman?: string | null
  decimals: number
}): bigint {
  if (args.onChainRaw > BigInt(0)) return args.onChainRaw

  const portalHuman = args.portalBalanceHuman?.trim()
  if (!portalHuman) return args.onChainRaw
  try {
    return parseLombardHumanAmountToRaw(portalHuman, args.decimals)
  } catch {
    return args.onChainRaw
  }
}
