/**
 * Client Lokalise minimal (TMS) — opt-in via env.
 *
 * Activation :
 *   - `LOKALISE_API_TOKEN`   : token API personnel ou bot (https://app.lokalise.com/profile)
 *   - `LOKALISE_PROJECT_ID`  : ID du projet Lokalise (URL admin Lokalise)
 *
 * Aucun fichier n'envoie ou ne reçoit quoi que ce soit si l'une de ces deux
 * variables est absente — les scripts CLI (`i18n:lokalise:push|pull`)
 * s'arrêteront avec un message explicite.
 *
 * On utilise uniquement les endpoints publics REST :
 *   - POST /projects/{id}/files/upload   (push d'un ARB par locale)
 *   - POST /projects/{id}/files/download (pull bundle ZIP via S3)
 *
 * Référence : https://developers.lokalise.com/reference/
 *
 * **Stratégie d'identité** : on fait du round-tripping basé sur les keys
 * canoniques (`<namespace>.<segments…>`) — c'est exactement la convention
 * Lokalise. Le format ARB conserve les metadata (description, placeholders).
 */

const LOKALISE_BASE_URL = 'https://api.lokalise.com/api2'

export type LokaliseConfig = {
  apiToken: string
  projectId: string
}

export function readLokaliseConfig(): LokaliseConfig | null {
  const apiToken = process.env.LOKALISE_API_TOKEN?.trim()
  const projectId = process.env.LOKALISE_PROJECT_ID?.trim()
  if (!apiToken || !projectId) return null
  return { apiToken, projectId }
}

async function lokaliseFetch(
  cfg: LokaliseConfig,
  pathSuffix: string,
  init: RequestInit = {},
): Promise<unknown> {
  const url = `${LOKALISE_BASE_URL}/projects/${encodeURIComponent(cfg.projectId)}${pathSuffix}`
  const headers = new Headers(init.headers)
  headers.set('X-Api-Token', cfg.apiToken)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Lokalise ${res.status} ${res.statusText} on ${pathSuffix} — ${body.slice(0, 400)}`)
  }
  return res.json()
}

export type LokaliseUploadFileParams = {
  filename: string
  /// Contenu ARB sérialisé. Le SDK l'attend en base64.
  arbContent: string
  /// ISO de la locale (`en`, `fr`, …) — doit exister dans le projet Lokalise.
  langIso: string
}

/**
 * Push d'un fichier ARB. Lokalise crée/merge les keys :
 *   - Si la key existe → met à jour la traduction de cette locale.
 *   - Sinon → crée la key (avec source = locale par défaut du projet).
 *
 * On force `convert_placeholders=false` car on conserve `{count}` ICU à
 * l'identique (compatible Flutter ARB).
 */
export async function lokaliseUploadArb(
  cfg: LokaliseConfig,
  params: LokaliseUploadFileParams,
): Promise<{ processId: string }> {
  const data = Buffer.from(params.arbContent, 'utf8').toString('base64')
  const body = {
    data,
    filename: params.filename,
    lang_iso: params.langIso,
    convert_placeholders: false,
    detect_icu_plurals: true,
    use_automations: false,
    /// Marquer les uploads venant du CMS pour différencier visuellement
    /// dans Lokalise (recherche par tag).
    tags: ['cms-ui-strings'],
    apply_tm: true,
  }
  const json = (await lokaliseFetch(cfg, '/files/upload', {
    method: 'POST',
    body: JSON.stringify(body),
  })) as { process: { process_id: string } }
  return { processId: json.process.process_id }
}

/**
 * Demande la génération d'un bundle de download (toutes locales, format ARB).
 * Renvoie l'URL S3 du ZIP (signed, expire ~1 mois).
 *
 * Pas de polling nécessaire : Lokalise garantit que `bundle_url` est prêt à
 * la réponse de cet appel synchrone.
 */
export async function lokaliseDownloadBundle(
  cfg: LokaliseConfig,
): Promise<{ bundleUrl: string }> {
  const body = {
    format: 'arb',
    original_filenames: false,
    bundle_structure: 'app_%LANG_ISO%.%FORMAT%',
    /// Compact = ne pas exporter les metadata Lokalise (context, comments)
    /// — on ré-attache nos propres metadata ARB au moment du re-import.
    compact: false,
    /// Inclure les keys traduites uniquement (pas les "untranslated" qui
    /// pourraient écraser nos sourceText).
    filter_data: ['translated'],
    indentation: '2sp',
  }
  const json = (await lokaliseFetch(cfg, '/files/download', {
    method: 'POST',
    body: JSON.stringify(body),
  })) as { bundle_url: string }
  return { bundleUrl: json.bundle_url }
}
