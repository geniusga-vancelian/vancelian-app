/**
 * Messages d’erreur BFF exposés au client — pas de détails de schéma DB / colonnes internes.
 */

/** Action refusée : droits CMS (ex. custody) — message orienté utilisateur. */
export const BFF_ERROR_CMS_ACTION_FORBIDDEN =
  'Vous êtes connecté au CMS, mais votre compte n’est pas autorisé à effectuer cette action. Contactez un administrateur si nécessaire.'

/**
 * Identité API / configuration BFF indisponible pour cette action (routes non migrées
 * vers le compte de service, ou configuration serveur incomplète).
 */
export const BFF_ERROR_BACKEND_IDENTITY_UNAVAILABLE =
  'Cette action n’est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur.'
