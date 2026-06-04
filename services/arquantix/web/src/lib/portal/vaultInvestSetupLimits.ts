/** Plafonds affichés / validés à l’écran setup invest vault (FR). */

export type VaultClientDepositLimits = {
  minDepositUsdc: number
  maxDepositUsdc: number
  maxUserExposureUsdc: number
}

export function resolveEffectiveVaultDepositMax(args: {
  walletUsdc: number
  vaultPositionUsdc: number
  limits?: VaultClientDepositLimits | null
}): number {
  const wallet = Math.max(0, args.walletUsdc)
  if (!args.limits) return wallet

  const perTx = Math.max(0, args.limits.maxDepositUsdc)
  const exposureHeadroom = Math.max(
    0,
    args.limits.maxUserExposureUsdc - Math.max(0, args.vaultPositionUsdc),
  )
  return Math.min(wallet, perTx, exposureHeadroom)
}

export function validateVaultDepositSetupAmount(args: {
  amount: number
  walletUsdc: number
  vaultPositionUsdc: number
  limits?: VaultClientDepositLimits | null
}): string | null {
  if (!Number.isFinite(args.amount) || args.amount <= 0) {
    return 'Saisissez un montant valide.'
  }

  const wallet = Math.max(0, args.walletUsdc)
  if (args.amount > wallet + 1e-9) {
    return wallet > 0
      ? `Montant maximum disponible : ${formatUsdcAmount(wallet)} USDC.`
      : 'Aucun USDC disponible pour investir sur ce coffre.'
  }

  if (!args.limits) return null

  if (args.amount + 1e-9 < args.limits.minDepositUsdc) {
    return `Dépôt minimum : ${formatUsdcAmount(args.limits.minDepositUsdc)} USDC.`
  }

  if (args.amount > args.limits.maxDepositUsdc + 1e-9) {
    return `Dépôt maximum par opération : ${formatUsdcAmount(args.limits.maxDepositUsdc)} USDC.`
  }

  const exposureHeadroom = args.limits.maxUserExposureUsdc - Math.max(0, args.vaultPositionUsdc)
  if (args.amount > exposureHeadroom + 1e-9) {
    return `Exposition maximum atteinte (${formatUsdcAmount(args.limits.maxUserExposureUsdc)} USDC sur ce coffre).`
  }

  return null
}

/** Message jaune (setup) quand le montant saisi dépasse le plafond affiché. */
export function vaultSetupExceedsMaxWarning(args: {
  amount: number
  maxAmount: number
  assetSymbol: string
  kind: 'deposit' | 'withdraw'
}): string | null {
  if (!Number.isFinite(args.amount) || args.amount <= 0) return null
  const max = Math.max(0, args.maxAmount)
  if (args.amount <= max + 1e-9) return null

  const symbol = args.assetSymbol.trim() || 'USDC'
  const maxLabel = formatTokenAmount(max)
  const amountLabel = formatTokenAmount(args.amount)

  if (args.kind === 'withdraw') {
    if (max <= 0) {
      return 'Aucun fonds retirable dans ce coffre pour le moment.'
    }
    return `Votre demande (${amountLabel} ${symbol}) dépasse le maximum retirable. Montant maximum disponible : ${maxLabel} ${symbol}.`
  }

  if (max <= 0) {
    return 'Aucun USDC disponible pour investir sur ce coffre.'
  }
  return `Votre demande (${amountLabel} ${symbol}) dépasse le montant disponible. Montant maximum : ${maxLabel} ${symbol}.`
}

export function validateVaultWithdrawSetupAmount(args: {
  amount: number
  vaultBalanceUsdc: number
  assetSymbol: string
}): string | null {
  if (!Number.isFinite(args.amount) || args.amount <= 0) {
    return 'Saisissez un montant valide.'
  }

  const max = Math.max(0, args.vaultBalanceUsdc)
  const symbol = args.assetSymbol.trim() || 'USDC'
  if (args.amount > max + 1e-9) {
    return max > 0
      ? `Montant maximum retirable : ${formatTokenAmount(max)} ${symbol}.`
      : 'Aucun fonds retirable dans ce coffre pour le moment.'
  }

  return null
}

function formatTokenAmount(value: number): string {
  return value.toLocaleString('fr-FR', {
    minimumFractionDigits: value % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  })
}

/** @deprecated alias interne dépôt */
function formatUsdcAmount(value: number): string {
  return formatTokenAmount(value)
}
