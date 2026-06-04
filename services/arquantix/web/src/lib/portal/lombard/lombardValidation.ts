import { z } from 'zod'

import { normalizeLombardBorrowAmountForApi } from '@/lib/portal/lombard/lombardBorrowUi'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { idempotencyKeySchema } from '@/lib/portal/morphoVaultValidation'

const lombardBorrowAmountSchema = z
  .string()
  .trim()
  .transform((value) => normalizeLombardBorrowAmountForApi(value) ?? '')
  .pipe(z.string().min(1, 'Invalid borrow amount.'))

export const lombardCollateralSchema = z.enum(['cbBTC', 'cbETH'])

export const lombardTargetLtvPercentSchema = z.coerce
  .number()
  .int()
  .min(1, 'Target LTV must be at least 1%.')
  .max(70, 'Target LTV cannot exceed 70%.')

const lombardPortalCollateralBalanceSchema = z
  .string()
  .trim()
  .max(32)
  .optional()
  .transform((value) => (value ? value : undefined))

export const lombardCapacityQuerySchema = z.object({
  collateral: lombardCollateralSchema,
  walletAddress: z.string().trim().refine(isValidEvmAddress, 'Invalid wallet address.'),
  targetLtvPercent: lombardTargetLtvPercentSchema,
  portalWalletCollateralBalance: lombardPortalCollateralBalanceSchema,
})

export const lombardQuoteSchema = z.object({
  collateral: lombardCollateralSchema,
  borrowAmount: lombardBorrowAmountSchema,
  walletAddress: z.string().trim().refine(isValidEvmAddress, 'Invalid wallet address.'),
  targetLtvPercent: lombardTargetLtvPercentSchema,
  portalWalletCollateralBalance: lombardPortalCollateralBalanceSchema,
})

export const lombardPrepareSchema = lombardQuoteSchema.extend({
  idempotencyKey: idempotencyKeySchema,
  logicalBorrowId: idempotencyKeySchema.optional(),
  retryOfGroupKey: idempotencyKeySchema.optional(),
  retryAttemptNumber: z.coerce.number().int().min(0).max(4).optional(),
})

export { idempotencyKeySchema }
