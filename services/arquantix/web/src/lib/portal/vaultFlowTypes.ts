/** Scène UX Vault (R4.5-D) — distincte des phases d’exécution on-chain. */
export type PortalVaultFlowScene = 'setup' | 'review' | 'processing' | 'result'

export type PortalVaultOperation = 'deposit' | 'withdraw'

export type PortalVaultExecutionPhase =
  | 'idle'
  | 'preparing'
  | 'approval_pending'
  | 'deposit_pending'
  | 'withdraw_pending'
  | 'confirming'
  | 'confirmed'
  | 'failed'
