/**
 * Dry-run : pour chaque type de section du catalogue, parse `defaultData`
 * avec le schéma Zod puis exécute `mapDataToComponentProps`.
 *
 * Aucune écriture base de données. Sortie : erreurs sur stderr, code 1 si échec.
 *
 * Usage : `npm run scripts:section-dry-run`
 */
import { SECTION_TYPES } from '../src/lib/sections/library'
import { mapDataToComponentProps } from '../src/lib/sections/mapDataToComponentProps'

let failures = 0

for (const t of SECTION_TYPES) {
  const parsed = t.zodSchema.safeParse(t.defaultData)
  if (!parsed.success) {
    console.error(`[${t.key}] Zod defaultData:`, parsed.error.flatten())
    failures++
    continue
  }
  try {
    mapDataToComponentProps(t.key, parsed.data, 'fr')
  } catch (err) {
    console.error(`[${t.key}] mapDataToComponentProps:`, err)
    failures++
  }
}

if (failures > 0) {
  console.error(`\nsection-data-dry-run : ${failures} erreur(s).`)
  process.exit(1)
}

console.log(`section-data-dry-run : OK (${SECTION_TYPES.length} types).`)
