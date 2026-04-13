/**
 * Regulatory scope jurisdictions
 * 
 * Naming convention: <Company>_<Region>_<Regulator>_<License?>
 * 
 * This avoids confusion between different regulators in the same region
 * (e.g., DIFC vs VARA in UAE).
 */

export interface JurisdictionOption {
  value: string
  label: string
}

export const REGULATORY_JURISDICTIONS: JurisdictionOption[] = [
  {
    value: 'Arquantix_UAE_DIFC_cat4_crowdfunding',
    label: 'Arquantix – UAE – DIFC – Cat 4 – Crowdfunding',
  },
  {
    value: 'Vancelian_UAE_VARA',
    label: 'Vancelian – UAE – VARA',
  },
  {
    value: 'Vancelian_EU_MICA',
    label: 'Vancelian – EU – MiCA',
  },
]

/**
 * Check if a jurisdiction value is in the known regulatory scope list
 */
export function isKnownJurisdiction(jurisdiction: string | null | undefined): boolean {
  if (!jurisdiction) return false
  return REGULATORY_JURISDICTIONS.some((j) => j.value === jurisdiction)
}

/**
 * Get the display label for a jurisdiction, or return a safe fallback
 */
export function getJurisdictionLabel(jurisdiction: string | null | undefined): string {
  if (!jurisdiction) return 'Unknown'
  const known = REGULATORY_JURISDICTIONS.find((j) => j.value === jurisdiction)
  if (known) return known.label
  return `Unknown / Legacy jurisdiction (${jurisdiction})`
}
