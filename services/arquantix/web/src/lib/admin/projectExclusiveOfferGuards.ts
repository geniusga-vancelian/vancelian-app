/**
 * Phase 8 — Garde-fous : ne plus créer d’Exclusive Offer via le flux Projects / create-from-project.
 *
 * Variables :
 * - `ADMIN_BLOCK_PROJECT_BASED_EO=true` — bloque POST /api/admin/projects et proxy create-from-project
 * - `ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true` — rollback contrôlé (prioritaire sur le blocage)
 *
 * Côté client (bannières / boutons), utiliser en parallèle :
 * - `NEXT_PUBLIC_ADMIN_BLOCK_PROJECT_BASED_EO=true` (même intention, figé au build Next)
 */
export function isProjectBasedExclusiveOfferCreationBlocked(): boolean {
  const block = process.env.ADMIN_BLOCK_PROJECT_BASED_EO === 'true'
  const allow = process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO === 'true'
  return block && !allow
}
