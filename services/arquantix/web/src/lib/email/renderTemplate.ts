import { renderMjmlFile } from './mjmlRender'
import {
  interpolate,
  prepareVarsForMjml,
  validateVars,
} from './interpolate'
import { EMAIL_TEMPLATES, getEmailTemplate } from './templateRegistry'
import type {
  EmailLocale,
  EmailTemplateId,
  RenderedEmail,
} from './types'

export interface RenderTemplateInput<TId extends EmailTemplateId> {
  templateId: TId
  locale: EmailLocale
  vars: unknown
  /** Pour debug : indenter le HTML produit. */
  beautify?: boolean
}

/**
 * Pipeline standard de rendu d’un template MJML :
 *
 * 1. Lookup du template dans `EMAIL_TEMPLATES`.
 * 2. Validation **stricte** des variables via Zod (refuse l’input IA invalide).
 * 3. Lecture + interpolation Mustache du fichier MJML.
 * 4. Compilation MJML → HTML (validation strict côté MJML aussi).
 * 5. Sujet localisé via la fonction du registry.
 * 6. Génération d’une variante texte minimale.
 *
 * Pas d’envoi ici : appeler ensuite `sendAdapter.send({ to, subject, html, text })`.
 */
export async function renderTemplate<TId extends EmailTemplateId>(
  input: RenderTemplateInput<TId>,
): Promise<RenderedEmail> {
  const template = getEmailTemplate(input.templateId)
  if (!template) {
    throw new Error(`Unknown email template id: ${input.templateId}`)
  }

  /**
   * Validation Zod : la valeur retournée correspond à `z.infer<varsSchema>`.
   * Le registry est typé strictement par template, donc `template.subject`
   * attend exactement le même type. On ponte via `unknown` pour aligner les
   * types nominaux (TS ne réconcilie pas systématiquement deux inférences
   * Zod indépendantes même si structurellement identiques).
   */
  const vars = validateVars(template.varsSchema, input.vars)
  const safeVars = prepareVarsForMjml(vars as unknown as Record<string, unknown>)

  const mjmlSource = await readTemplateSource(template.mjmlPath)
  const { loadEmailPartials } = await import('./loadPartials')
  const partials = await loadEmailPartials()
  const interpolatedMjml = interpolate(mjmlSource, safeVars, partials)
  const { renderMjmlString, MJML_PATHS } = await import('./mjmlRender')
  const path = await import('node:path')
  const { html } = await renderMjmlString(interpolatedMjml, {
    validationLevel: 'strict',
    beautify: !!input.beautify,
    filePath: path.dirname(path.join(MJML_PATHS.mjml, template.mjmlPath)),
  })

  const subjectFn = template.subject as (vars: unknown, locale: EmailLocale) => string
  const subject = subjectFn(vars, input.locale)
  const text = htmlToPlainText(html)

  return {
    subject,
    html,
    text,
    locale: input.locale,
    templateId: input.templateId,
  }
}

async function readTemplateSource(relativePath: string): Promise<string> {
  const { promises: fs } = await import('node:fs')
  const path = await import('node:path')
  const { MJML_PATHS } = await import('./mjmlRender')
  const abs = path.join(MJML_PATHS.mjml, relativePath)
  return fs.readFile(abs, 'utf8')
}

/**
 * Variante texte ultra-simple — fallback pour clients qui ne lisent pas l’HTML.
 * On ne vise pas la perfection, juste un contenu lisible.
 */
function htmlToPlainText(html: string): string {
  return html
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<head[\s\S]*?<\/head>/gi, '')
    .replace(/<\/(p|div|tr|li|h1|h2|h3|h4|h5|h6|section|article)>/gi, '\n')
    .replace(/<br\s*\/?>(\s*)/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export const EMAIL_TEMPLATE_IDS_LIST = Object.keys(EMAIL_TEMPLATES) as EmailTemplateId[]
