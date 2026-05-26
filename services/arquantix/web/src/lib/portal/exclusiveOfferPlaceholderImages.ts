/** Images de repli pour cartes offre exclusive (immobilier / investissement). */
const EXCLUSIVE_OFFER_PLACEHOLDER_IMAGES = [
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?auto=format&fit=crop&w=800&q=80',
] as const

function hashSeed(seed: string): number {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  }
  return hash
}

export function pickExclusiveOfferPlaceholderImage(seed: string): string {
  const index = hashSeed(seed.trim() || 'default') % EXCLUSIVE_OFFER_PLACEHOLDER_IMAGES.length
  return EXCLUSIVE_OFFER_PLACEHOLDER_IMAGES[index]!
}

export function resolveExclusiveOfferCoverUrl(
  coverUrl: string | null | undefined,
  seed: string,
): string {
  const trimmed = coverUrl?.trim()
  return trimmed || pickExclusiveOfferPlaceholderImage(seed)
}
