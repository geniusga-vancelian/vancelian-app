/**
 * Layout pur des colonnes méga-menu (données déjà résolues côté serveur).
 */
export type MegaMenuItemPayload = {
  id: string
  title: string
  description: string
  href: string
  iconUrl?: string | null
}

export type MegaMenuColumnPayload = {
  id: string
  /** Libellé de colonne (catégorie). Absent = pas d’en-tête Figma. */
  category?: string
  items: MegaMenuItemPayload[]
}

type ItemWithCategory = MegaMenuItemPayload & { category: string }

function stripCategory(it: ItemWithCategory): MegaMenuItemPayload {
  const { category: _c, ...rest } = it
  return rest
}

/**
 * Règles produit :
 * - Moins de 2 entrées → pas de méga-menu (appelant renvoie null avant).
 * - ≥ 2 catégories non vides distinctes → 1 colonne par catégorie (+ colonne sans titre pour les non classés s’il y en a).
 * - Sinon → 2 colonnes en répartissant les items (moitié / moitié).
 */
export function layoutMegaMenuColumns(
  items: ItemWithCategory[],
): MegaMenuColumnPayload[] {
  if (items.length < 2) {
    return []
  }

  const nonEmptyCats = new Set<string>()
  for (const it of items) {
    const c = it.category.trim()
    if (c) nonEmptyCats.add(c)
  }

  if (nonEmptyCats.size >= 2) {
    const byCat = new Map<string, ItemWithCategory[]>()
    const uncat: ItemWithCategory[] = []

    for (const it of items) {
      const c = it.category.trim()
      if (!c) {
        uncat.push(it)
        continue
      }
      if (!byCat.has(c)) byCat.set(c, [])
      byCat.get(c)!.push(it)
    }

    const columns: MegaMenuColumnPayload[] = []
    let colIndex = 0

    if (uncat.length > 0) {
      columns.push({
        id: `mega-col-${colIndex++}`,
        category: undefined,
        items: uncat.map(stripCategory),
      })
    }

    const sortedCats = [...nonEmptyCats].sort((a, b) => a.localeCompare(b))
    for (const cat of sortedCats) {
      const raw = byCat.get(cat) ?? []
      if (raw.length === 0) continue
      columns.push({
        id: `mega-col-${colIndex++}`,
        category: cat,
        items: raw.map(stripCategory),
      })
    }

    return columns
  }

  const mid = Math.ceil(items.length / 2)
  return [
    {
      id: 'mega-col-a',
      category: undefined,
      items: items.slice(0, mid).map(stripCategory),
    },
    {
      id: 'mega-col-b',
      category: undefined,
      items: items.slice(mid).map(stripCategory),
    },
  ]
}
