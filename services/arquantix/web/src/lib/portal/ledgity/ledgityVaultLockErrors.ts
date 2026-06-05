export class LedgityVaultLockError extends Error {
  readonly code = 'ledgity.withdraw_lock_active'
  readonly status = 422

  constructor(
    message = 'Cette offre exclusive est en période de lock-up (club deal). Les retraits seront disponibles à la maturité.',
  ) {
    super(message)
    this.name = 'LedgityVaultLockError'
  }
}
