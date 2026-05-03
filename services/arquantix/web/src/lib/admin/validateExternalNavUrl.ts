/**
 * Validation stricte des URLs pour les entrées menu `EXTERNAL_LINK` (admin uniquement).
 * Autorisé : http(s) absolu. Refuse javascript:, data:, mailto:, file:, etc.
 */
export type ExternalNavUrlResult =
  | { ok: true; url: string }
  | { ok: false; error: string }

export function normalizeExternalNavUrl(input: string): ExternalNavUrlResult {
  const trimmed = input.trim()
  if (!trimmed) {
    return {
      ok: false,
      error: 'L’URL externe est obligatoire pour un lien externe.',
    }
  }

  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    return {
      ok: false,
      error: 'URL invalide : utilisez une adresse absolue (ex. https://example.com).',
    }
  }

  const protocol = parsed.protocol.toLowerCase()
  if (protocol !== 'http:' && protocol !== 'https:') {
    return {
      ok: false,
      error: 'Seuls les protocoles http:// et https:// sont autorisés pour un lien de navigation.',
    }
  }

  return { ok: true, url: parsed.href }
}
