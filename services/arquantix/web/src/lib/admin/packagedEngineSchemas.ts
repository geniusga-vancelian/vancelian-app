import { z } from 'zod'

/** POST .../engine/lending/create — corps aligné sur create-from-packaged-product (Python). */
export const createLendingFromPackagedBodySchema = z.object({
  borrower_client_id: z.string().uuid(),
  asset: z.string().min(1).max(20),
  target_size: z.number().positive(),
  title: z.string().max(200).optional().nullable(),
  supply_apr_bps: z.number().min(0).max(100_000).default(300),
  borrow_apr_bps: z.number().min(0).max(100_000).default(500),
  min_ticket: z.number().positive().optional().nullable(),
  max_ticket: z.number().positive().optional().nullable(),
})

export type CreateLendingFromPackagedBody = z.infer<typeof createLendingFromPackagedBodySchema>

export const linkLendingBodySchema = z.object({
  lending_product_id: z.string().uuid(),
})

export const linkVaultBodySchema = z.object({
  portal_config_id: z.string().min(1).max(64),
})
