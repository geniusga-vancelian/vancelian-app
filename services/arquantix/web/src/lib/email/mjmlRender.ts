import path from 'node:path'
import { promises as fs } from 'node:fs'
import { createRequire } from 'node:module'

/**
 * MJML v5 ne fournit pas d’ESM stable et son binding TypeScript par défaut
 * exporte une signature non alignée avec l’API runtime async. On charge donc
 * le module CJS via `createRequire` et on type localement la fonction.
 */
const requireCjs = createRequire(import.meta.url)

type MjmlError = {
  line: number
  message: string
  tagName?: string
  formattedMessage?: string
}

type MjmlResult = {
  html?: string
  errors?: MjmlError[]
  json?: unknown
}

type MjmlOptions = {
  validationLevel?: 'strict' | 'soft' | 'skip'
  beautify?: boolean
  minify?: boolean
  filePath?: string
  keepComments?: boolean
}

type MjmlFn = (mjml: string, options?: MjmlOptions) => Promise<MjmlResult> | MjmlResult

const mjml2html = requireCjs('mjml') as MjmlFn

const EMAILS_ROOT = path.resolve(process.cwd(), 'emails')
const MJML_ROOT = path.join(EMAILS_ROOT, 'mjml')

export interface MjmlRenderOptions {
  /** Validation MJML : `strict` casse à la moindre erreur (défaut), `soft` warn, `skip` aucun contrôle. */
  validationLevel?: 'strict' | 'soft' | 'skip'
  /** Indenter le HTML produit (utile pour debug, off en prod). */
  beautify?: boolean
  /** Minifier (économise quelques Ko, désactivé par défaut pour lisibilité). */
  minify?: boolean
  /** Surcharge optionnelle de `filePath` pour la résolution `<mj-include>`. */
  filePath?: string
}

export interface MjmlRenderResult {
  html: string
  errors: ReadonlyArray<{ line: number; message: string; tagName?: string }>
}

/**
 * Compile un fragment MJML en HTML, in-process (pas de spawn npx mjml).
 * Lance `MjmlValidationError` si `validationLevel: 'strict'` et que MJML retourne des erreurs.
 */
export async function renderMjmlString(
  mjmlSource: string,
  options: MjmlRenderOptions = {},
): Promise<MjmlRenderResult> {
  const { validationLevel = 'strict', beautify = false, minify = false, filePath } = options

  let result: MjmlResult
  try {
    result = await Promise.resolve(
      mjml2html(mjmlSource, {
        validationLevel,
        minify,
        beautify,
        filePath: filePath ?? MJML_ROOT,
        keepComments: false,
      }),
    )
  } catch (rawError) {
    /**
     * En mode strict, MJML v5 lève **synchroniquement** une `ValidationError`
     * (pas dans `result.errors`). On la capture pour exposer notre type
     * `MjmlValidationError` partout dans le pipeline.
     */
    if (validationLevel === 'strict') {
      const raw = rawError as { message?: string }
      const msg = raw?.message ?? String(rawError)
      throw new MjmlValidationError(`MJML strict validation failed: ${msg}`, [
        { line: 0, message: msg },
      ])
    }
    throw rawError
  }

  const errors = result.errors ?? []
  if (validationLevel === 'strict' && errors.length > 0) {
    const summary = errors
      .map((e) => `L${e.line} <${e.tagName ?? '?'}>: ${e.message}`)
      .join('\n')
    throw new MjmlValidationError(`MJML strict validation failed:\n${summary}`, errors)
  }

  return {
    html: result.html ?? '',
    errors,
  }
}

/**
 * Charge un fichier `.mjml` (chemin **relatif** à `emails/mjml/`) puis le compile.
 * Exemple : `renderMjmlFile('templates/newsletter-quarterly.mjml')`.
 */
export async function renderMjmlFile(
  relativePath: string,
  options: MjmlRenderOptions = {},
): Promise<MjmlRenderResult> {
  const absolutePath = path.join(MJML_ROOT, relativePath)
  const source = await fs.readFile(absolutePath, 'utf8')
  return renderMjmlString(source, {
    ...options,
    filePath: options.filePath ?? path.dirname(absolutePath),
  })
}

export class MjmlValidationError extends Error {
  readonly errors: ReadonlyArray<{ line: number; message: string; tagName?: string }>
  constructor(
    message: string,
    errors: ReadonlyArray<{ line: number; message: string; tagName?: string }>,
  ) {
    super(message)
    this.name = 'MjmlValidationError'
    this.errors = errors
  }
}

export const MJML_PATHS = {
  root: EMAILS_ROOT,
  mjml: MJML_ROOT,
  templates: path.join(MJML_ROOT, 'templates'),
  components: path.join(MJML_ROOT, 'components'),
  layouts: path.join(MJML_ROOT, 'layouts'),
  partials: path.join(MJML_ROOT, 'partials'),
  fixtures: path.join(EMAILS_ROOT, 'fixtures'),
  rendered: path.join(EMAILS_ROOT, 'rendered'),
} as const
