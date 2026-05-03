import { NextResponse, type NextRequest } from 'next/server'
import { z } from 'zod'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { getSessionFromCookie } from '@/lib/auth'
import { openai, OPENAI_MODEL } from '@/lib/openai/client'
import {
  EMAIL_TEMPLATES,
  renderTemplate,
  SUPPORTED_EMAIL_LOCALES,
} from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  type EmailLocale,
  type EmailTemplateId,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'
import {
  EmailTemplateVarsError,
} from '@/lib/email/interpolate'
import { MjmlValidationError } from '@/lib/email/mjmlRender'
import { EMAIL_COMPONENTS } from '@/lib/email/componentCatalog'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
/**
 * Le prompt IA peut être verbeux : on coupe à 4096 jetons en sortie pour
 * limiter les coûts et le risque de truncation JSON.
 */
const MAX_OUTPUT_TOKENS = 4096
const MAX_REPAIR_ATTEMPTS = 2

const bodySchema = z.object({
  templateId: z.enum(EMAIL_TEMPLATE_IDS),
  locale: z.enum(SUPPORTED_EMAIL_LOCALES).default('fr'),
  prompt: z.string().min(3).max(4000),
  /**
   * Variables précédentes (mode itératif) : si fournies, l’IA part de cette
   * base et applique seulement les modifications demandées par `prompt`.
   */
  previousVars: z.record(z.string(), z.unknown()).optional(),
})

interface SuccessResponse {
  ok: true
  templateId: EmailTemplateId
  locale: EmailLocale
  vars: Record<string, unknown>
  subject: string
  html: string
  warnings: string[]
  model: string
  usage?: { inputTokens?: number; outputTokens?: number }
}

interface ErrorResponse {
  ok: false
  error: string
  code: 'INVALID_INPUT' | 'OPENAI_ERROR' | 'INVALID_VARS' | 'MJML_INVALID' | 'INTERNAL'
  details?: unknown
}

export async function POST(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  let parsed
  try {
    const json = await request.json()
    parsed = bodySchema.parse(json)
  } catch (err) {
    return NextResponse.json<ErrorResponse>(
      {
        ok: false,
        error: 'Invalid request body',
        code: 'INVALID_INPUT',
        details: err instanceof z.ZodError ? err.issues : String(err),
      },
      { status: 400 },
    )
  }

  const template = EMAIL_TEMPLATES[parsed.templateId]
  const fixture = await loadFixtureVars(parsed.templateId)
  if (!fixture) {
    return NextResponse.json<ErrorResponse>(
      { ok: false, error: `Fixture introuvable pour ${parsed.templateId}`, code: 'INTERNAL' },
      { status: 500 },
    )
  }

  /**
   * Stratégie : few-shot grounding via la fixture canonique du template.
   * - System prompt : décrit le rôle, les contraintes, les composants disponibles
   *   et impose un JSON strict conforme au schéma (avec exemple).
   * - User prompt : la demande métier + locale.
   * - Si `previousVars` est fourni, on le passe comme base à modifier.
   *
   * Le LLM répond en JSON pur (response_format: json_object), validé par Zod.
   * En cas d’échec Zod, on tente jusqu’à `MAX_REPAIR_ATTEMPTS` réparations
   * en repassant les erreurs à l’IA.
   */
  const systemPrompt = buildSystemPrompt(parsed.templateId, fixture, parsed.previousVars)
  const userPrompt = `Locale cible: ${parsed.locale}\n\nDemande utilisateur:\n"""${parsed.prompt}"""`

  const messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userPrompt },
  ]

  let llmJsonText = ''
  let usage: SuccessResponse['usage']
  try {
    const completion = await openai.chat.completions.create({
      model: OPENAI_MODEL,
      temperature: 0.4,
      max_tokens: MAX_OUTPUT_TOKENS,
      response_format: { type: 'json_object' },
      messages,
    })
    llmJsonText = completion.choices[0]?.message?.content ?? ''
    usage = {
      inputTokens: completion.usage?.prompt_tokens,
      outputTokens: completion.usage?.completion_tokens,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json<ErrorResponse>(
      { ok: false, error: `OpenAI: ${msg}`, code: 'OPENAI_ERROR' },
      { status: 502 },
    )
  }

  let varsCandidate: Record<string, unknown>
  try {
    varsCandidate = JSON.parse(llmJsonText) as Record<string, unknown>
  } catch (err) {
    return NextResponse.json<ErrorResponse>(
      {
        ok: false,
        error: 'Sortie OpenAI non-JSON',
        code: 'OPENAI_ERROR',
        details: { rawHead: llmJsonText.slice(0, 200) },
      },
      { status: 502 },
    )
  }

  // 2 tours de réparation si le JSON ne valide pas le schéma Zod
  let zodIssues: z.ZodIssue[] | null = null
  for (let attempt = 0; attempt <= MAX_REPAIR_ATTEMPTS; attempt += 1) {
    const parsedVars = template.varsSchema.safeParse({
      ...varsCandidate,
      locale: parsed.locale,
    })
    if (parsedVars.success) {
      try {
        const r = await renderTemplate({
          templateId: parsed.templateId,
          locale: parsed.locale,
          vars: parsedVars.data,
          beautify: true,
        })
        return NextResponse.json<SuccessResponse>({
          ok: true,
          templateId: parsed.templateId,
          locale: parsed.locale,
          vars: parsedVars.data as unknown as Record<string, unknown>,
          subject: r.subject,
          html: r.html,
          warnings: [],
          model: OPENAI_MODEL,
          usage,
        })
      } catch (err) {
        if (err instanceof MjmlValidationError) {
          return NextResponse.json<ErrorResponse>(
            { ok: false, error: err.message, code: 'MJML_INVALID', details: err.errors },
            { status: 502 },
          )
        }
        if (err instanceof EmailTemplateVarsError) {
          return NextResponse.json<ErrorResponse>(
            {
              ok: false,
              error: err.message,
              code: 'INVALID_VARS',
              details: err.zodError.issues,
            },
            { status: 422 },
          )
        }
        const msg = err instanceof Error ? err.message : String(err)
        return NextResponse.json<ErrorResponse>(
          { ok: false, error: msg, code: 'INTERNAL' },
          { status: 500 },
        )
      }
    }

    zodIssues = parsedVars.error.issues
    if (attempt === MAX_REPAIR_ATTEMPTS) break

    // Tour de réparation : on rappelle l’IA avec les erreurs.
    const repairPrompt = `Le JSON précédent ne valide pas le schéma. Corrige les erreurs ci-dessous et renvoie un nouveau JSON COMPLET conforme au schéma.

Erreurs:
${zodIssues.map((i) => `- ${i.path.join('.') || '<root>'}: ${i.message}`).join('\n')}

JSON précédent (à corriger):
${JSON.stringify(varsCandidate, null, 2)}`

    try {
      const repair = await openai.chat.completions.create({
        model: OPENAI_MODEL,
        temperature: 0.2,
        max_tokens: MAX_OUTPUT_TOKENS,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
          { role: 'assistant', content: llmJsonText },
          { role: 'user', content: repairPrompt },
        ],
      })
      llmJsonText = repair.choices[0]?.message?.content ?? ''
      varsCandidate = JSON.parse(llmJsonText)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      return NextResponse.json<ErrorResponse>(
        { ok: false, error: `OpenAI repair: ${msg}`, code: 'OPENAI_ERROR' },
        { status: 502 },
      )
    }
  }

  return NextResponse.json<ErrorResponse>(
    {
      ok: false,
      error: `Le JSON produit par l’IA n’a pas pu être validé après ${MAX_REPAIR_ATTEMPTS + 1} tentatives.`,
      code: 'INVALID_VARS',
      details: zodIssues,
    },
    { status: 422 },
  )
}

/* ------------------------------------------------------------------ */

async function loadFixtureVars(
  id: EmailTemplateId,
): Promise<{ vars: Record<string, unknown> } | null> {
  try {
    const raw = await fs.readFile(
      path.join(MJML_PATHS.fixtures, `${id}.json`),
      'utf8',
    )
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function buildSystemPrompt(
  templateId: EmailTemplateId,
  fixture: { vars: Record<string, unknown> },
  previousVars: Record<string, unknown> | undefined,
): string {
  const template = EMAIL_TEMPLATES[templateId]
  const jsonSchema = z.toJSONSchema(template.varsSchema)
  const componentsList = EMAIL_COMPONENTS.map(
    (c) => `- ${c.id} (${c.kind}) — ${c.description}`,
  ).join('\n')

  const baseExample = previousVars ?? fixture.vars

  return `Tu es Email Architect IA pour Arquantix, un produit fintech premium (vaults d'actifs réels, custody on-chain, copy haut de gamme et concise).

Ton rôle : générer un objet JSON de variables qui sera injecté dans le template MJML "${templateId}" puis rendu en HTML d'envoi via un pipeline strict (Mustache + MJML + validation Zod).

CONTRAINTES ABSOLUES:
1. Tu DOIS retourner UNIQUEMENT un objet JSON valide, sans aucun texte autour, sans markdown, sans bloc \`\`\`json.
2. Le JSON DOIT respecter strictement le JSON Schema fourni ci-dessous (longueurs max, regex, URLs, énumérations).
3. Tous les champs marqués \`required\` DOIVENT être présents.
4. Les URLs DOIVENT être absolues (https://...).
5. La copy DOIT être en ${'<locale>'} = locale demandée par l'utilisateur (fr ou en).
6. Style: premium fintech, clean, concis, professionnel. Pas d'emojis sauf demande explicite.
7. Pour les CTA: labels courts (max 40 caractères), action claire ("Read the letter", "Open client space"…).
8. Si l'utilisateur ne précise pas une donnée, utilise une valeur réaliste cohérente avec un produit Arquantix premium (vaults, gold, real estate, custody, etc.).
9. Si un champ a un format strict (ex: OTP doit être 4-8 chiffres), respecte-le.
10. Préheader: court, max 140 caractères, donne l'envie de lire.

JSON SCHEMA À RESPECTER:
${JSON.stringify(jsonSchema, null, 2)}

EXEMPLE COMPLET DE JSON VALIDE (à utiliser comme référence de structure et de ton):
${JSON.stringify(baseExample, null, 2)}

COMPOSANTS MJML DISPONIBLES dans ce template (pour info — tu ne les choisis pas, tu fournis seulement les variables):
${componentsList}

${
  previousVars
    ? "MODE ITÉRATIF : tu pars du JSON précédent (l'EXEMPLE ci-dessus EST le JSON précédent) et tu n'appliques QUE les modifications demandées par l'utilisateur. Tous les champs non concernés restent identiques."
    : 'MODE INITIAL : tu génères un JSON complet inspiré du style de la référence, en adaptant la copy à la demande utilisateur.'
}

Réponds UNIQUEMENT avec le JSON.`
}
