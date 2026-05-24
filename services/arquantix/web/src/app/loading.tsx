/**
 * Pas d’écran plein page entre site public et portail (/app/*).
 * Le layout racine refetch le menu CMS au changement de surface — un fallback
 * ici provoquait un flash blanc « Chargement… » indésirable.
 */
export default function Loading() {
  return null
}
