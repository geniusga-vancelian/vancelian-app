/**
 * Scanner i18n générique de chaînes user-facing hardcodées.
 *
 * Logique commune mutualisée entre :
 *   - `vaultHardcodedStringsScanner` (périmètre `components/exclusive-offer/**`),
 *   - `siteHardcodedStringsScanner`  (périmètre site public : header / footer / sections).
 *
 * Convention rappelée :
 *   - Contenu spécifique à un module / une page → prop CMS traduisible.
 *   - Libellé générique d'UI                    → registre `*CommonCta(locale, key)`.
 *   - Aucun texte user-facing hardcodé dans le rendu JSX du périmètre cible.
 *
 * Volontairement léger (regex sur le source brut, pas d'AST) :
 *   - périmètres restreints,
 *   - aligné sur les autres tests `node --import tsx --test ...` du repo,
 *   - exceptions justifiées via commentaires `i18n-allow…`.
 *
 * Allowlist :
 *   - `// i18n-allow-next-line: <raison>`            (commentaire JS standard)
 *   - `{/* i18n-allow-next-line: <raison> *\u002F}`  (commentaire JSX, naturel en .tsx)
 *   - `// i18n-allow-file: <raison>` ou `{/* i18n-allow-file: <raison> *\u002F}` en
 *     n'importe quel point du fichier désactive l'analyse complète (à n'utiliser
 *     que pour les fichiers debug / showcase / admin).
 */

import fs from 'node:fs'
import path from 'node:path'

export type HardcodedFinding = {
  /** Chemin absolu du fichier */
  file: string
  /** 1-based */
  line: number
  /** Type de violation */
  kind:
    | 'jsx-text'
    | 'attr-aria-label'
    | 'attr-title'
    | 'attr-alt'
    | 'attr-placeholder'
  /** Texte litigieux extrait */
  snippet: string
  /** Ligne complète (trim) pour contexte */
  rawLine: string
}

/**
 * Marqueur d'allowlist sur la ligne suivante. Accepte les deux formats :
 *   - `// i18n-allow-next-line: <raison>`            (commentaire JS standard)
 *   - `{/* i18n-allow-next-line: <raison> *\u002F}`  (commentaire JSX)
 */
const ALLOW_NEXT_LINE_RE = /i18n-allow-next-line(?:\s*:.*)?(?:\s*\*\/\s*\})?$/
const ALLOW_FILE_RE = /i18n-allow-file(?:\s*:.*)?/

/**
 * Texte JSX visible : `>....<` sur une seule ligne, sans accolade `{`/`}`.
 */
const JSX_TEXT_RE = />([^<>{}]+)</g

const SENSITIVE_ATTRS = ['aria-label', 'title', 'alt', 'placeholder'] as const
type SensitiveAttr = (typeof SENSITIVE_ATTRS)[number]

const ATTR_KIND: Record<SensitiveAttr, HardcodedFinding['kind']> = {
  'aria-label': 'attr-aria-label',
  title: 'attr-title',
  alt: 'attr-alt',
  placeholder: 'attr-placeholder',
}

function buildAttrRegex(attr: string): RegExp {
  return new RegExp(`\\b${attr}\\s*=\\s*"([^"]*)"`, 'g')
}

/**
 * Heuristique : ressemble à du langage naturel destiné à l'utilisateur.
 * - Au moins 2 lettres alphabétiques consécutives (latin + diacritiques courants).
 * - Aucun caractère de syntaxe technique (`/`, `=`, `;`) ⇒ filtre paths / classes Tailwind.
 * - Aucune parenthèse `(`/`)` ⇒ filtre les fragments JSX ternaires capturés
 *   accidentellement entre deux balises (ex. `) : cond ? (`).
 */
function looksLikeUserFacingText(raw: string): boolean {
  const t = raw.trim()
  if (t.length === 0) return false
  if (!/[A-Za-zÀ-ÖØ-öø-ÿ]{2,}/.test(t)) return false
  if (/[/=;()]/.test(t)) return false
  return true
}

/**
 * Vérifie si la position `pos` dans `line` est à l'intérieur d'une balise JSX
 * ouverte (présence d'un `<` non fermé par `>` avant la position).
 *
 * Permet de distinguer un véritable attribut JSX (`<Foo title="...">`) d'une
 * valeur par défaut de paramètre TS (`function X({ title = "FAQ" })`),
 * et d'éviter les faux positifs sur les signatures.
 *
 * Limitation assumée : si la balise s'ouvre sur une ligne précédente
 * (mise en forme multi-lignes des attributs), `prevLineOpensTag` permet
 * de propager l'état d'une ligne sur l'autre.
 */
function isPositionInJsxTag(
  line: string,
  pos: number,
  prevLineOpensTag: boolean,
): boolean {
  let open = prevLineOpensTag ? 1 : 0
  for (let i = 0; i < pos && i < line.length; i++) {
    const c = line[i]
    if (c === '<') open++
    else if (c === '>') open = Math.max(0, open - 1)
  }
  return open > 0
}

/**
 * Vrai si la ligne se termine dans un état "balise JSX ouverte" (un `<` n'a
 * pas encore son `>` correspondant). Utilisé pour propager l'état entre lignes
 * pour la détection d'attributs en mise en forme multi-ligne.
 */
function lineEndsInOpenJsxTag(line: string, prevOpen: boolean): boolean {
  let open = prevOpen ? 1 : 0
  for (const c of line) {
    if (c === '<') open++
    else if (c === '>') open = Math.max(0, open - 1)
  }
  return open > 0
}

function lineContainsJsxExpression(line: string): boolean {
  return /\{[^}]*\}/.test(line)
}

function isCommentLine(line: string): boolean {
  const t = line.trim()
  if (t.startsWith('//') || t.startsWith('/*') || t.startsWith('*')) return true
  if (t.startsWith('{/*') && t.endsWith('*/}')) return true
  return false
}

/**
 * Texte JSX multi-ligne : `<p>\n  Texte\n</p>`.
 * Cas où le texte est seul sur sa ligne, sans aucune balise ni interpolation.
 * On ne signale que si la ligne précédente semble "ouvrir" un contexte JSX
 * (se termine par `>` non auto-fermant et n'est pas une expression).
 */
function isStandaloneJsxTextLine(line: string): boolean {
  const t = line.trim()
  if (t.length === 0) return false
  if (/[<>{}]/.test(t)) return false
  return looksLikeUserFacingText(t)
}

function previousLineOpensJsxContext(prevLine: string | undefined): boolean {
  if (!prevLine) return false
  const t = prevLine.trimEnd()
  if (t.length === 0) return false
  if (!t.endsWith('>')) return false
  if (t.endsWith('/>')) return false
  if (t.endsWith('=>')) return false
  return true
}

/**
 * Scanne un fichier et retourne la liste des chaînes user-facing hardcodées.
 * Si `source` est fourni, l'utilise plutôt que de relire le fichier (utile pour les tests).
 */
export function scanFileForHardcodedStrings(
  filePath: string,
  source?: string,
): HardcodedFinding[] {
  const content = source ?? fs.readFileSync(filePath, 'utf8')
  const lines = content.split(/\r?\n/)
  const findings: HardcodedFinding[] = []

  if (ALLOW_FILE_RE.test(content)) {
    return findings
  }

  let prevLineIsAllowAnnotation = false
  let prevLineOpensTag = false

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ''
    const trimmed = line.trim()
    const startedInsideTag = prevLineOpensTag

    if (isCommentLine(line)) {
      prevLineIsAllowAnnotation = ALLOW_NEXT_LINE_RE.test(trimmed)
      // Les commentaires ne modifient pas l'état "balise ouverte"
      continue
    }

    if (prevLineIsAllowAnnotation) {
      prevLineIsAllowAnnotation = false
      prevLineOpensTag = lineEndsInOpenJsxTag(line, startedInsideTag)
      continue
    }

    for (const attr of SENSITIVE_ATTRS) {
      const re = buildAttrRegex(attr)
      let m: RegExpExecArray | null
      while ((m = re.exec(line)) !== null) {
        const value = m[1] ?? ''
        if (!looksLikeUserFacingText(value)) continue
        // Évite les faux positifs sur les valeurs par défaut de paramètres TS
        // (`function X({ title = "FAQ" })`) qui ne sont pas des attributs JSX.
        if (!isPositionInJsxTag(line, m.index, startedInsideTag)) continue
        findings.push({
          file: filePath,
          line: i + 1,
          kind: ATTR_KIND[attr],
          snippet: value,
          rawLine: trimmed,
        })
      }
    }

    if (!lineContainsJsxExpression(line)) {
      let m: RegExpExecArray | null
      while ((m = JSX_TEXT_RE.exec(line)) !== null) {
        const value = m[1] ?? ''
        if (!looksLikeUserFacingText(value)) continue
        findings.push({
          file: filePath,
          line: i + 1,
          kind: 'jsx-text',
          snippet: value.trim(),
          rawLine: trimmed,
        })
      }
    }

    if (
      isStandaloneJsxTextLine(line) &&
      previousLineOpensJsxContext(lines[i - 1])
    ) {
      findings.push({
        file: filePath,
        line: i + 1,
        kind: 'jsx-text',
        snippet: trimmed,
        rawLine: trimmed,
      })
    }

    prevLineOpensTag = lineEndsInOpenJsxTag(line, startedInsideTag)
  }

  return findings
}

export type ScanScope = {
  /** Répertoire racine à scanner (récursif `.tsx`). */
  rootDir: string
  /** Chemins absolus de fichiers à exclure (ex. fixtures, showcases). */
  excludeFiles?: string[]
  /** Sous-dossiers à exclure (chemins absolus, match par préfixe). */
  excludeDirs?: string[]
}

function listTsxFilesRecursive(
  rootDir: string,
  excludeDirs: string[] = [],
): string[] {
  const out: string[] = []
  function walk(dir: string) {
    if (excludeDirs.some((d) => dir === d || dir.startsWith(`${d}${path.sep}`))) {
      return
    }
    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        walk(full)
      } else if (entry.isFile() && entry.name.endsWith('.tsx')) {
        out.push(full)
      }
    }
  }
  walk(rootDir)
  return out
}

/**
 * Scanne un (ou plusieurs) périmètre(s) et retourne la liste agrégée des findings.
 */
export function scanScopes(scopes: ScanScope[]): HardcodedFinding[] {
  const all: HardcodedFinding[] = []
  for (const scope of scopes) {
    const excludeSet = new Set(scope.excludeFiles ?? [])
    const files = listTsxFilesRecursive(scope.rootDir, scope.excludeDirs ?? [])
    for (const f of files) {
      if (excludeSet.has(f)) continue
      all.push(...scanFileForHardcodedStrings(f))
    }
  }
  return all
}

export function formatFindingsForReport(
  findings: HardcodedFinding[],
  baseDir?: string,
): string {
  if (findings.length === 0) return ''
  return findings
    .map((f) => {
      const rel = baseDir ? path.relative(baseDir, f.file) : f.file
      return `  - ${rel}:${f.line} [${f.kind}] "${f.snippet}"`
    })
    .join('\n')
}
