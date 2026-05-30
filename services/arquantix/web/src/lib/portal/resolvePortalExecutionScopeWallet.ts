import type { ExecutionWallet } from '@/lib/wallet/executionWalletTypes'

/** Adresse d'exécution portail (backend / scope) sans session SDK Privy. */
export async function resolvePortalExecutionScopeWallet(
  resolveExecutionWallet: () => Promise<ExecutionWallet | null>,
): Promise<ExecutionWallet> {
  const wallet = await resolveExecutionWallet()
  if (!wallet?.address) {
    throw new Error(
      'No execution wallet found. Open My crypto wallet, set up your wallet, then try again.',
    )
  }
  return wallet
}
