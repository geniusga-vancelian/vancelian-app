/**
 * Backend URL helper for Next.js API routes
 * Standardizes how we construct backend URLs for FastAPI
 */

/**
 * Get the base URL for the FastAPI backend
 */
export function getBackendBaseUrl(): string {
  // Server-side : DNS Docker (arquantix-api) via BACKEND_* — jamais localhost dans le conteneur.
  // Ordre : BACKEND_API_URL → BACKEND_INTERNAL_URL → BACKEND_URL → NEXT_PUBLIC_* (navigateur / fallback dev)
  const backendUrl =
    process.env.BACKEND_API_URL ||
    process.env.BACKEND_INTERNAL_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    'http://127.0.0.1:8000'
  const resolved = backendUrl === 'http://localhost:8000' ? 'http://127.0.0.1:8000' : backendUrl
  
  // Remove trailing slash
  return resolved.replace(/\/$/, '')
}

/**
 * Build a full backend URL from a path
 * @param path - Path like '/api/ai/email/compose' (with leading slash)
 * @returns Full URL like 'http://localhost:8000/api/ai/email/compose'
 */
export function buildBackendUrl(path: string): string {
  const baseUrl = getBackendBaseUrl()
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${normalizedPath}`
}

/**
 * Pour logs diagnostics (ex. proxy PDF) : quelle variable a déterminé la base URL.
 * Doit rester aligné sur l’ordre de `getBackendBaseUrl()`.
 */
export function getBackendUrlResolution(): {
  source: 'BACKEND_API_URL' | 'BACKEND_INTERNAL_URL' | 'BACKEND_URL' | 'NEXT_PUBLIC_BACKEND_URL' | 'default'
  baseUrl: string
} {
  const baseUrl = getBackendBaseUrl()
  if (process.env.BACKEND_API_URL) {
    return { source: 'BACKEND_API_URL', baseUrl }
  }
  if (process.env.BACKEND_INTERNAL_URL) {
    return { source: 'BACKEND_INTERNAL_URL', baseUrl }
  }
  if (process.env.BACKEND_URL) {
    return { source: 'BACKEND_URL', baseUrl }
  }
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return { source: 'NEXT_PUBLIC_BACKEND_URL', baseUrl }
  }
  return { source: 'default', baseUrl }
}


