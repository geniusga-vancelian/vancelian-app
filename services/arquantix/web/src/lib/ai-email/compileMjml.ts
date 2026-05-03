/**
 * Compile MJML → HTML — **in-process** via le package `mjml` installé localement.
 *
 * Conserve **strictement** la signature historique `(mjml) → { html, error }`
 * pour ne casser aucun appelant existant (admin builder, EmailModule preview…).
 *
 * Migration :
 *  - Avant : `spawn('npx', ['--yes', 'mjml', '-i', '-'])` à chaque appel
 *            (fragile : timeout 15s, dépendance réseau npx, latence forte).
 *  - Après : `mjml2html(source, { validationLevel: 'soft' })` synchroniquement,
 *            pas de spawn, pas de filesystem temporaire.
 *
 * Validation : `soft` par défaut pour préserver le comportement historique
 * (les anciens specs ne sont pas tous strict-conformes). Pour un contrôle
 * strict, utiliser plutôt le pipeline `src/lib/email/renderTemplate.ts`.
 */
import { renderMjmlString } from '@/lib/email/mjmlRender'

export async function compileMjml(
  mjml: string,
): Promise<{ html: string; error: string | null }> {
  try {
    const r = await renderMjmlString(mjml, {
      validationLevel: 'soft',
      beautify: false,
      minify: false,
    })
    if (r.errors.length > 0) {
      const summary = r.errors
        .map((e) => `L${e.line} <${e.tagName ?? '?'}>: ${e.message}`)
        .join('; ')
      console.warn('[MJML] Compilation warnings:', summary)
    }
    if (!r.html) {
      const msg = 'No HTML output from MJML'
      return { html: generateFallbackHtml(msg), error: msg }
    }
    return { html: r.html, error: null }
  } catch (rawError) {
    const msg = rawError instanceof Error ? rawError.message : String(rawError)
    console.error('[MJML] Compilation error:', msg)
    return { html: generateFallbackHtml(msg), error: msg }
  }
}

function generateFallbackHtml(errorMsg: string): string {
  return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Preview</title>
</head>
<body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 4px;">
        <h2 style="color: #d32f2f; margin-bottom: 20px;">MJML Compilation Error</h2>
        <p style="color: #666; line-height: 1.6;">${escapeHtml(errorMsg)}</p>
        <p style="color: #999; font-size: 14px; margin-top: 20px;">Voir les logs serveur pour plus de détails.</p>
    </div>
</body>
</html>`
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
