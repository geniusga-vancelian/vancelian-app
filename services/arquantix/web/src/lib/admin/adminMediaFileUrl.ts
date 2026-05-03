/**
 * URL same-origin pour afficher un média dans l’admin (session cookie).
 * Évite les URLs présignées R2 / domaines publics cassés (bucket privé, mauvaise config).
 */
export function adminMediaFileUrl(mediaId: string): string {
  return `/api/admin/media/${mediaId}/file`
}
