import { z } from 'zod'

import {
  isValidEvmAddress,
  LEDGITY_CHAIN_ID,
  normalizeVaultAddress,
  type PortalLedgityIntegrationMode,
} from '@/lib/portal/ledgity/ledgityConstants'

export const integrationModeSchema = z.literal('ledgity_vault')

export const createLedgityVaultSchema = z
  .object({
    vaultAddress: z.string().trim().refine(isValidEvmAddress, 'Adresse vault Base invalide.'),
    chainId: z.number().int().positive().default(LEDGITY_CHAIN_ID),
    integrationMode: integrationModeSchema.default('ledgity_vault'),
    privyVaultId: z.string().trim().optional().nullable(),
    label: z.string().trim().max(120).optional().nullable(),
    description: z.string().trim().max(2000).optional().nullable(),
    curator: z.string().trim().max(120).optional().nullable(),
    sortOrder: z.number().int().min(0).optional(),
    isPublished: z.boolean().optional(),
  })
  .superRefine((value, ctx) => {
    if (value.chainId !== LEDGITY_CHAIN_ID) {
      ctx.addIssue({
        code: 'custom',
        message: 'Seule la chaîne Base (8453) est supportée en v1.',
        path: ['chainId'],
      })
    }
  })

export const updateLedgityVaultSchema = z.object({
  integrationMode: integrationModeSchema.optional(),
  privyVaultId: z.string().trim().optional().nullable(),
  label: z.string().trim().max(120).optional().nullable(),
  description: z.string().trim().max(2000).optional().nullable(),
  curator: z.string().trim().max(120).optional().nullable(),
  sortOrder: z.number().int().min(0).optional(),
  isPublished: z.boolean().optional(),
})

export const prepareLedgityTxSchema = z.object({
  vaultAddress: z.string().trim().refine(isValidEvmAddress, 'Adresse vault invalide.'),
  walletAddress: z.string().trim().refine(isValidEvmAddress, 'Adresse wallet invalide.'),
  operation: z.enum(['deposit', 'withdraw']),
  amount: z
    .string()
    .trim()
    .refine((value) => /^\d+(\.\d+)?$/.test(value.replace(',', '.')) && Number(value.replace(',', '.')) > 0, {
      message: 'Montant invalide.',
    }),
  idempotencyKey: z
    .string()
    .trim()
    .min(8, 'idempotency_key requis (min. 8 caractères).')
    .max(128, 'idempotency_key trop long.'),
})

export const idempotencyKeySchema = z
  .string()
  .trim()
  .min(8, 'idempotency_key requis (min. 8 caractères).')
  .max(128, 'idempotency_key trop long.')

export function normalizeCreateLedgityVaultInput(input: z.infer<typeof createLedgityVaultSchema>) {
  return {
    vaultAddress: normalizeVaultAddress(input.vaultAddress),
    chainId: LEDGITY_CHAIN_ID,
    integrationMode: input.integrationMode as PortalLedgityIntegrationMode,
    privyVaultId: input.privyVaultId?.trim() || null,
    label: input.label?.trim() || null,
    description: input.description?.trim() || null,
    curator: input.curator?.trim() || null,
    sortOrder: input.sortOrder ?? 999,
    isPublished: input.isPublished ?? false,
  }
}
