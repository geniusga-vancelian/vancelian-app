import { classifySwapError } from '@/lib/portal/swapFailure'
import {
  type SwapConfirmExecutePayload,
  type SwapQuotePayload,
  SwapPriceChangedError,
  confirmSwapExecution,
} from '@/lib/portal/swapClient'

const MAX_ATTEMPTS = 3
const RETRY_DELAY_MS = 600

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isRetryableError(error: unknown): boolean {
  if (error instanceof SwapPriceChangedError) return false
  if (error instanceof Error) {
    if (error.message.includes('Session expirée')) return false
    if ((error as Error & { retryable?: boolean }).retryable) return true
    if (error.message.includes('fetch') || error.message.includes('network')) return true
  }
  return false
}

export async function confirmSwapWithRetry(
  input: {
    swap_id: string
    review_estimated_receive: string
    review_amount_in?: string
  },
  options?: { maxAttempts?: number },
): Promise<SwapConfirmExecutePayload> {
  const maxAttempts = Math.max(1, options?.maxAttempts ?? MAX_ATTEMPTS)
  let lastError: unknown
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await confirmSwapExecution(input)
    } catch (error) {
      lastError = error
      if (!isRetryableError(error) || attempt >= maxAttempts - 1) {
        if (error instanceof SwapPriceChangedError) {
          throw error
        }
        throw classifySwapError(error, 'confirm_execute')
      }
      await sleep(RETRY_DELAY_MS * (attempt + 1))
    }
  }
  throw lastError
}

export type SwapReviewSnapshot = {
  estimated_receive: string
  amount_in: string
}

export function buildSwapReviewSnapshot(quote: SwapQuotePayload): SwapReviewSnapshot {
  return {
    estimated_receive: quote.estimated_receive,
    amount_in: quote.amount_in,
  }
}

export { SwapPriceChangedError }
