import Mustache from 'mustache'
import { z } from 'zod'

/**
 * Désactive le HTML escaping global de Mustache pour les **template MJML** :
 * MJML produit déjà du HTML structurel (balises `<mj-*>`) et nous voulons que
 * `{{tagline}}` insère un texte brut tel quel — l’échappement est appliqué une
 * dernière fois sur les valeurs **scalaires utilisateur** via `escapeHtml()`
 * dans `prepareVarsForMjml()` ci-dessous, pour conserver la sécurité.
 *
 * Dans la sortie HTML finale, on laisse Mustache tagger comme `{{ }}` (escape
 * actif) sur les valeurs déjà inline pour double-sécurité.
 *
 * Voir https://github.com/janl/mustache.js#variables — section *unescape*.
 */
const MUSTACHE_TAGS: [string, string] = ['{{', '}}']

/**
 * Substitue les variables `{{var}}` dans un MJML / HTML déjà rendu.
 * - Les valeurs scalaires sont **HTML-escapées** par défaut (Mustache `{{var}}`).
 * - Pour insérer du HTML brut, utiliser `{{{var}}}` côté template (à utiliser
 *   uniquement avec des valeurs **vérifiées par schéma**).
 *
 * Le 3ᵉ argument `partials` permet d’injecter des fragments réutilisables :
 * dans le template, écrire `{{> Button}}` ou `{{> head}}` ; Mustache résout
 * la clé `Button` / `head` dans `partials`.
 */
export function interpolate(
  source: string,
  vars: Record<string, unknown>,
  partials?: Record<string, string>,
): string {
  return Mustache.render(source, vars, partials, MUSTACHE_TAGS)
}

/**
 * Sanitize / coerce les variables avant injection.
 * - Remplace `null` / `undefined` par `''` pour éviter `[Object object]`.
 * - Conserve les nombres et booléens (Mustache les stringify).
 * - Préserve les arrays (utilisés par `{{#items}}…{{/items}}`).
 */
export function prepareVarsForMjml(vars: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(vars)) {
    if (value === null || value === undefined) {
      out[key] = ''
    } else if (Array.isArray(value)) {
      out[key] = value
    } else if (typeof value === 'object') {
      out[key] = value
    } else {
      out[key] = value
    }
  }
  return out
}

/**
 * Valide un objet de variables avec un schéma Zod et lève une erreur explicite
 * si invalide. Utilisé par `renderTemplate()` pour garantir la qualité des
 * variables passées par les appelants (en particulier l’IA chat).
 */
export function validateVars<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  vars: unknown,
): z.infer<TSchema> {
  const parsed = schema.safeParse(vars)
  if (!parsed.success) {
    const messages = parsed.error.issues
      .map((i) => `• ${i.path.join('.') || '<root>'}: ${i.message}`)
      .join('\n')
    throw new EmailTemplateVarsError(
      `Variables invalides pour le template :\n${messages}`,
      parsed.error,
    )
  }
  return parsed.data
}

export class EmailTemplateVarsError extends Error {
  readonly zodError: z.ZodError
  constructor(message: string, zodError: z.ZodError) {
    super(message)
    this.name = 'EmailTemplateVarsError'
    this.zodError = zodError
  }
}
