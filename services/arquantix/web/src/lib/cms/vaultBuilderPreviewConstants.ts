/**
 * Query d’aperçu Vault Builder (`?adminDraftPreview=1`). Réservé à l’iframe depuis le CMS :
 * la page projet ne lève les garde-fous « offre exclusive » **_que si_** `getSessionFromCookie()`
 * est valide pour la même requête (`projectDetailPageContent`).
 */
export const VAULT_BUILDER_IFRAME_PREVIEW_QUERY = 'adminDraftPreview' as const
