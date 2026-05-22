/**
 * Segments racine qui ne doivent PAS être redirigés vers `/fr/{segment}` (routes hors périmètre CMS préfixé phase 2B).
 * Les autres chemins `/slug` (un seul segment) → `/fr/slug` (308).
 */
export const LEGACY_UNPREFIXED_TOP_LEVEL = new Set([
  'projects',
  'help',
  'design',
  'figma',
  'chat',
  'kyc',
  'preview',
  'guide',
  'qa-difficiles',
  'admin',
  'app',
  'dashboard',
  'health',
])
