/**
 * Taille de page effective pour `blog_mosaic` : multiple de 3.
 * 0 et les valeurs ≤ 0 ne sont pas des multiples de 3 → 3.
 */
export function normalizeBlogMosaicLimit(raw: unknown): number {
  const n = typeof raw === 'number' && Number.isFinite(raw) ? raw : NaN
  if (!Number.isFinite(n) || n <= 0) return 3
  return Math.ceil(n / 3) * 3
}
