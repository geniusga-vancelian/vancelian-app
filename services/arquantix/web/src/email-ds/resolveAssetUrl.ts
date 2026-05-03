/**
 * Construit l’URL d’un fichier sous `public/email-ds/`.
 * Pour l’envoi réel (SMTP, ESP), passer `origin` = origine publique (ex. https://www.arquantix.com).
 */
export function emailDsAssetUrl(file: string, origin?: string): string {
  const path = `/email-ds/${file.replace(/^\//, '')}`
  if (!origin) return path
  return `${origin.replace(/\/$/, '')}${path}`
}
