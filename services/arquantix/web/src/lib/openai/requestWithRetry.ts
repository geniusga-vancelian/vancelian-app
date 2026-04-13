import OpenAI from 'openai'

const MAX_RETRIES = 2 // Max 3 attempts total (initial + 2 retries)
const BASE_BACKOFF_MS = 400
const MAX_BACKOFF_MS = 1200
const JITTER_MS = 200

/**
 * Retryable status codes
 */
const RETRYABLE_STATUS_CODES = [429, 500, 502, 503, 504]

/**
 * Add jitter to backoff delay
 */
function addJitter(delay: number): number {
  return delay + Math.floor(Math.random() * JITTER_MS)
}

/**
 * Calculate backoff delay for attempt number (0-indexed)
 */
function getBackoffDelay(attempt: number): number {
  const baseDelay = BASE_BACKOFF_MS * Math.pow(2, attempt)
  const cappedDelay = Math.min(baseDelay, MAX_BACKOFF_MS)
  return addJitter(cappedDelay)
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: any): boolean {
  // Network/timeout errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true
  }

  // OpenAI API errors with status codes
  if (error?.status && RETRYABLE_STATUS_CODES.includes(error.status)) {
    return true
  }

  // OpenAI error objects
  if (error?.response?.status && RETRYABLE_STATUS_CODES.includes(error.response.status)) {
    return true
  }

  return false
}

/**
 * Extract status code from error
 */
function getStatusCode(error: any): number | null {
  return error?.status || error?.response?.status || null
}

/**
 * Wrapper for OpenAI API calls with retry logic
 */
export async function requestWithRetry<T>(
  fn: () => Promise<T>,
  context?: string
): Promise<T> {
  let lastError: any = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await fn()
    } catch (error: any) {
      lastError = error

      // Don't retry on last attempt
      if (attempt === MAX_RETRIES) {
        break
      }

      // Check if error is retryable
      if (!isRetryableError(error)) {
        // Not retryable, throw immediately
        break
      }

      // Calculate delay and wait
      const delay = getBackoffDelay(attempt)
      const statusCode = getStatusCode(error)

      // Dev logs only
      if (process.env.NODE_ENV !== 'production') {
        console.log(
          `[OpenAI Retry] ${context || 'Request'} - Attempt ${attempt + 1}/${MAX_RETRIES + 1} failed${statusCode ? ` (${statusCode})` : ''}, retrying in ${delay}ms...`
        )
      }

      await new Promise((resolve) => setTimeout(resolve, delay))
    }
  }

  // All retries exhausted or non-retryable error
  const statusCode = getStatusCode(lastError)
  const errorMessage = lastError?.message || 'Unknown error'

  // Preserve original error structure
  if (lastError instanceof Error) {
    const enhancedError = new Error(errorMessage)
    if (statusCode) {
      ;(enhancedError as any).status = statusCode
    }
    throw enhancedError
  }

  throw lastError
}


