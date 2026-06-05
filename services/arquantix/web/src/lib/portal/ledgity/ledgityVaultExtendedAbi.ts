/** ABI extensions FixedTermInvestmentVault / LedgityYieldVault (lock-up, file async). */

export const LEDGITY_VAULT_LOCK_ABI = [
  {
    type: 'function',
    name: 'operationEndDate',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    type: 'function',
    name: 'withdrawalRequestsEnabled',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    type: 'function',
    name: 'withdrawalGasFee',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    type: 'function',
    name: 'convertToShares',
    stateMutability: 'view',
    inputs: [{ name: 'assets', type: 'uint256' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    type: 'function',
    name: 'requestWithdrawal',
    stateMutability: 'payable',
    inputs: [{ name: 'shares', type: 'uint256' }],
    outputs: [],
  },
] as const
