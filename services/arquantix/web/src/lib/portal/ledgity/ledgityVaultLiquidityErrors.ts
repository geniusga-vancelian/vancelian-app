export class LedgityVaultLiquidityError extends Error {
  readonly code = 'ledgity.withdraw_liquidity_insufficient'
  readonly status = 422

  constructor(
    message = 'La liquidité disponible du vault ne permet pas un retrait instantané complet. Veuillez réessayer plus tard.',
  ) {
    super(message)
    this.name = 'LedgityVaultLiquidityError'
  }
}
