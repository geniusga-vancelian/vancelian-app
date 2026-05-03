/**
 * Phase d’affichage grille offres + libellés carte — **sans** import Prisma
 * (importable depuis des composants `"use client"`).
 */

export type ProjectGalleryOfferPhase = 'upcoming' | 'in_progress' | 'delivered'

/** Pastille sur l’image des cartes offres (dérivée du pool / `galleryOfferPhase`). */
export function offerGalleryPhaseToImageLabel(
  phase: ProjectGalleryOfferPhase | null | undefined,
): string {
  switch (phase) {
    case 'upcoming':
      return 'Coming soon'
    case 'in_progress':
      return 'Funding'
    case 'delivered':
      return 'Funded'
    default:
      return 'Coming soon'
  }
}
