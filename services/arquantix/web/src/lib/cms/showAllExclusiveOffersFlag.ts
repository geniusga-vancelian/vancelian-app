/**
 * Interprète le booléen CMS `showAllExclusiveOffers` pour `project_grid` / `projects`.
 *
 * Tolère du JSON hétérogène (copier-coller, migrations, API externes) : chaîne `"true"`,
 * `"1"`, nombre `1`. Sans cela, `value === true` échoue → la résolution DB des offres
 * exclusives est ignorée et la grille peut rester vide si `items` / sélection sont vides.
 */
export function readShowAllExclusiveOffersFlag(raw: unknown): boolean {
  if (raw === true) return true
  if (raw === false || raw == null) return false
  if (typeof raw === 'number' && raw === 1) return true
  if (typeof raw === 'string') {
    const s = raw.trim().toLowerCase()
    if (s === 'true' || s === '1' || s === 'yes') return true
  }
  return false
}
