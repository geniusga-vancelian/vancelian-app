import { z } from 'zod'

import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { idempotencyKeySchema } from '@/lib/portal/morphoVaultValidation'

export const lombardCollateralSchema = z.enum(['cbBTC', 'cbETH'])

export const lombardTargetLtvPercentSchema = z.coerce
  .number()
  .int()
  .min(1, 'Target LTV must be at least 1%.')
  .max(70, 'Target LTV cannot exceed 70%.')

export const lombardQuoteSchema = z.object({
  collateral: lombardCollateralSchema,
  borrowAmount: z
    .string()
    .trim()
    .refine((value) => /^\d+(\.\d+)?$/.test(value.replace(',', '.')) && Number(value.replace(',', '.')) > 0, {
      message: 'Invalid borrow amount.',
    }),
  walletAddress: z.string().trim().refine(isValidEvmAddress, 'Invalid wallet address.'),
  targetLtvPercent: lombardTargetLtvPercentSchema,
})

export const lombardPrepareSchema = lombardQuoteSchema.extend({
  idempotencyKey: idempotencyKeySchema,
})

export { idempotencyKeySchema }
