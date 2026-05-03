/**
 * Classification linguistique batchée via OpenAI — un appel pour N textes.
 *
 * Conçu pour fiabiliser le scan « Vérifier la langue » sur les champs courts
 * (eyebrows, labels, titres < ~24 chars) que `franc` ne sait pas trancher.
 *
 * Principes
 * ---------
 *
 *   - **Une seule requête OpenAI par scan** (et non un appel par champ) pour
 *     limiter le coût et la latence.
 *   - Réponse strictement JSON, validée à la réception. En cas de format
 *     invalide ou d'erreur réseau, on retourne `[]` : l'appelant retombe
 *     alors sur la classification heuristique locale (fallback gracieux).
 *   - Les textes sont tronqués à `MAX_TEXT_LEN` chars (200 par défaut). Sur
 *     un scan de page typique (~10–40 textes courts), une seule passe suffit.
 *   - **Au-delà de `MAX_BATCH_SIZE` items**, on fait plusieurs appels
 *     séquentiels (jamais parallèles, pour respecter les quotas).
 *
 * Volontairement découplé du domaine `pageCheckLanguage` : peut servir à
 * d'autres surfaces (Vault Builder, audit i18n) si besoin.
 */

import type OpenAI from 'openai'

import {
  openai,
  OPENAI_MODEL,
  OPENAI_TRANSLATION_TEMPERATURE,
} from '@/lib/openai/client'
import { requestWithRetry } from '@/lib/openai/requestWithRetry'

import type { Locale } from '@/config/locales'

type ChatCompletionNonStream = OpenAI.Chat.Completions.ChatCompletion

/** Identifiant opaque côté appelant — recopié dans la réponse. */
export type BatchClassifyItem = {
  id: string
  text: string
}

/**
 * Locale détectée pour un item.
 * - `'und'` si le LLM n'a pas pu trancher ou si l'item a été perdu.
 * - Sinon une `Locale` du périmètre (`fr` / `en` / `it`).
 */
export type BatchClassifyResult = {
  id: string
  locale: Locale | 'und'
  /** Score [0..1] — interprété indicativement, pas de seuil dur côté appelant. */
  confidence: number
}

export type BatchClassifyOutcome = {
  results: BatchClassifyResult[]
  /** Approximation `usage.total_tokens` cumulée sur tous les batchs. */
  tokensUsedApprox: number
  /** True si au moins un appel OpenAI a échoué — l'appelant doit afficher un avertissement. */
  hadError: boolean
  /** Nombre d'appels OpenAI effectivement émis (utile pour debug/observabilité). */
  callCount: number
}

const MAX_TEXT_LEN = 200
const MAX_BATCH_SIZE = 40
const MAX_TOKENS_PER_CALL = 1500

const SYSTEM_PROMPT = `You are a strict language classifier.

Given a JSON array of items \`[{ "id": string, "text": string }, …]\`,
return a JSON array of the same length with this exact shape:

\`[{ "id": string, "locale": "fr" | "en" | "it" | "und", "confidence": number }, …]\`

Rules:
- "fr" = French, "en" = English, "it" = Italian.
- Use "und" if the text is empty, only digits/punctuation, a brand name,
  a proper noun, or genuinely ambiguous (cannot tell among fr/en/it).
- "confidence" ∈ [0, 1]: 0.95+ when sure, 0.6–0.9 when reasonably sure,
  ≤0.5 when leaning but uncertain.
- Be especially careful with very short texts (< 10 chars): if the text
  contains French diacritics (é, è, à, ç, …) it is French. If it contains
  English-specific cues ("the", "and", "our", "team", "get", "started")
  it is English. Italian cues: "il", "della", "scopri", "grazie".
- The "id" field MUST be copied exactly from the input.
- Respond with ONLY the JSON array, no commentary, no markdown fences.`

function chunkBy<T>(arr: T[], size: number): T[][] {
  if (size <= 0) return [arr]
  const chunks: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size))
  }
  return chunks
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return text.slice(0, max)
}

function safeParseLLMArray(raw: string): unknown[] | null {
  // Le modèle peut parfois encadrer le JSON de fences markdown malgré
  // l'instruction. On nettoie de façon tolérante avant de parser.
  const cleaned = raw
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim()
  try {
    const parsed = JSON.parse(cleaned)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

function normalizeLocale(value: unknown): Locale | 'und' {
  if (value === 'fr' || value === 'en' || value === 'it') return value
  return 'und'
}

function normalizeConfidence(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0
  if (value < 0) return 0
  if (value > 1) return 1
  return Math.round(value * 100) / 100
}

async function classifyOneBatch(
  items: BatchClassifyItem[],
): Promise<{ results: BatchClassifyResult[]; tokensUsed: number }> {
  const userPayload = JSON.stringify(
    items.map((it) => ({ id: it.id, text: truncate(it.text, MAX_TEXT_LEN) })),
  )

  const response = (await requestWithRetry(
    () =>
      openai.chat.completions.create({
        model: OPENAI_MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userPayload },
        ],
        temperature: OPENAI_TRANSLATION_TEMPERATURE,
        max_tokens: MAX_TOKENS_PER_CALL,
        response_format: { type: 'json_object' },
        stream: false,
      }),
    `batchClassifyLanguages(${items.length})`,
  )) as ChatCompletionNonStream

  const tokensUsed = response.usage?.total_tokens ?? 0
  const content = response.choices[0]?.message?.content?.trim() ?? ''

  // Le modèle peut renvoyer soit un array direct, soit un objet
  // { "results": [...] } à cause de `response_format: json_object`.
  let arr: unknown[] | null = safeParseLLMArray(content)
  if (!arr) {
    try {
      const obj = JSON.parse(content) as Record<string, unknown>
      const candidate =
        (Array.isArray(obj?.results) && obj.results) ||
        (Array.isArray(obj?.items) && obj.items) ||
        (Array.isArray(obj?.data) && obj.data) ||
        null
      if (candidate) arr = candidate as unknown[]
    } catch {
      arr = null
    }
  }

  if (!arr) {
    return { results: [], tokensUsed }
  }

  // Indexe par id pour résister à un réordonnancement éventuel.
  const byId = new Map<string, BatchClassifyResult>()
  for (const raw of arr) {
    if (raw == null || typeof raw !== 'object') continue
    const obj = raw as Record<string, unknown>
    const id = typeof obj.id === 'string' ? obj.id : null
    if (!id) continue
    byId.set(id, {
      id,
      locale: normalizeLocale(obj.locale),
      confidence: normalizeConfidence(obj.confidence),
    })
  }

  // Renvoie strictement les items demandés, dans l'ordre d'entrée. Tout
  // item manquant côté réponse est rendu en `und` (signal au caller).
  const results: BatchClassifyResult[] = items.map(
    (it) =>
      byId.get(it.id) ?? {
        id: it.id,
        locale: 'und' as const,
        confidence: 0,
      },
  )
  return { results, tokensUsed }
}

/**
 * Classifie en une ou plusieurs requêtes OpenAI la langue de chaque item.
 *
 * Fiabilité garantie : retourne TOUJOURS un tableau de longueur égale à
 * l'entrée. En cas d'échec total, tous les items remontent en `und` avec
 * `confidence: 0` et `hadError: true`.
 */
export async function batchClassifyLanguages(
  items: BatchClassifyItem[],
): Promise<BatchClassifyOutcome> {
  if (items.length === 0) {
    return { results: [], tokensUsedApprox: 0, hadError: false, callCount: 0 }
  }

  const batches = chunkBy(items, MAX_BATCH_SIZE)
  const allResults: BatchClassifyResult[] = []
  let tokensUsedApprox = 0
  let hadError = false
  let callCount = 0

  for (const batch of batches) {
    callCount += 1
    try {
      const { results, tokensUsed } = await classifyOneBatch(batch)
      allResults.push(...results)
      tokensUsedApprox += tokensUsed
    } catch (err) {
      hadError = true
      console.error(
        `[batchClassifyLanguages] batch ${callCount}/${batches.length} failed:`,
        err,
      )
      // On dégrade en `und` pour TOUT le batch (fallback heuristique côté caller).
      for (const it of batch) {
        allResults.push({ id: it.id, locale: 'und', confidence: 0 })
      }
    }
  }

  return { results: allResults, tokensUsedApprox, hadError, callCount }
}

/** Type d'injection pour les tests : permet de mocker l'appel OpenAI. */
export type BatchLanguageRefiner = (
  items: BatchClassifyItem[],
) => Promise<BatchClassifyOutcome>
