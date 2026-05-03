/**
 * Heuristique : texte de démo / Lorem / latin classique — à dupliquer tel quel en EN/IT
 * plutôt que d’appeler le traducteur (évite de « traduire » le faux latin).
 */
export function isLoremIpsumOrLatinPlaceholder(combined: string): boolean {
  if (!combined || combined.length < 12) return false
  const t = combined.toLowerCase()
  if (/\blorem\s+ipsum\b/.test(t)) return true
  if (/\bipsum dolor sit amet\b/.test(t)) return true
  if (/\bconsectetur adipiscing elit\b/.test(t)) return true
  if (/\beiusmod tempor incididunt\b/.test(t)) return true
  if (/\bsed do eiusmod tempor\b/.test(t)) return true
  if (/\bduis aute irure dolor\b/.test(t)) return true
  if (/\bexcepteur sint occaecat\b/.test(t)) return true
  // Nombreux mots latins d’usage (Cicéron, texte de remplissage) sans mots modernes fr/en évidents
  const strip = t.replace(/[^a-zàâäéèêëïîôùûüç\s]/gi, ' ')
  const words = strip.split(/\s+/).filter(Boolean)
  if (words.length < 6) return false
  const latinish =
    /^(et|ut|in|ad|id|ac|ab|ex|de|ab|est|quis|quae|sunt|non|omnis|nemo|eodem|serenianus|tempore)$/i
  const hits = words.filter((w) => w.length > 2 && latinish.test(w)).length
  // Beaucoup de « mots » courts latins, peu de nombres / emails
  if (hits >= 4 && !/@|\d{4}/.test(t)) {
    if (/bonjour|le\s|la\s|les\s|dans|pour|avec|nous|vous/.test(t)) return false
    if (/\bthe\b|\band\b|with|from|this/.test(t)) return false
    if (/\bdigital|fintech|crypto|invest|march|blog/.test(t)) return false
    if (hits / words.length > 0.2) return true
  }
  return false
}
