import { z } from 'zod'

/** Clé idempotence portail — schéma pur (sans dépendance Morpho/Ledgity). */
export const idempotencyKeySchema = z
  .string()
  .trim()
  .min(8, 'idempotency_key requis (min. 8 caractères).')
  .max(128, 'idempotency_key trop long.')
