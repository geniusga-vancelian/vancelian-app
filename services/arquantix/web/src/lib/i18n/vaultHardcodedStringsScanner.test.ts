import assert from 'node:assert/strict'
import path from 'node:path'
import { describe, it } from 'node:test'

import {
  formatFindingsForReport,
  scanFileForHardcodedStrings,
  scanVaultExclusiveOfferDirectory,
} from '@/lib/i18n/vaultHardcodedStringsScanner'

const FAKE_PATH = '/virtual/example.tsx'

describe('vaultHardcodedStringsScanner — cas synthétiques', () => {
  it('détecte un texte JSX visible hardcodé', () => {
    const src = `
      export function X() {
        return <button>Download</button>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 1)
    assert.equal(findings[0]!.kind, 'jsx-text')
    assert.equal(findings[0]!.snippet, 'Download')
  })

  it('laisse passer une interpolation `{...}`', () => {
    const src = `
      export function X({ label }: { label: string }) {
        return <button>{label}</button>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('laisse passer une expression mixte `{a} {b}`', () => {
    const src = `
      export function X({ a, b }: { a: string; b: string }) {
        return <span>{a} {b}</span>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('détecte un aria-label hardcodé', () => {
    const src = `
      export function X() {
        return <button aria-label="Open menu" />
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 1)
    assert.equal(findings[0]!.kind, 'attr-aria-label')
    assert.equal(findings[0]!.snippet, 'Open menu')
  })

  it('laisse passer un aria-label dynamique `{...}`', () => {
    const src = `
      export function X({ label }: { label: string }) {
        return <button aria-label={label} />
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('détecte title, alt et placeholder hardcodés', () => {
    const src = `
      export function X() {
        return (
          <>
            <iframe title="YouTube video" />
            <img alt="Hero photo" />
            <input placeholder="Type here" />
          </>
        )
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    const kinds = findings.map((f) => f.kind).sort()
    assert.deepEqual(kinds, ['attr-alt', 'attr-placeholder', 'attr-title'])
  })

  it('laisse passer alt vide (cas autorisé pour image décorative)', () => {
    const src = `
      export function X() {
        return <img alt="" />
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('respecte `// i18n-allow-next-line` au-dessus de la ligne', () => {
    const src = `
      export function X() {
        return (
          <div>
            {/* fallback admin/debug : non user-facing en prod */}
            // i18n-allow-next-line: fallback admin debug
            <p>Module non reconnu</p>
          </div>
        )
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('respecte `// i18n-allow-file` en tête de fichier', () => {
    const src = `
      // i18n-allow-file: composant interne admin
      export function X() {
        return <p>Some hardcoded text</p>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('ne signale pas les chaînes non textuelles (classes, paths, ponctuation)', () => {
    const src = `
      export function X() {
        return (
          <div className="px-4 text-sm">
            <span>—</span>
            <span> · </span>
            <a href="/path/to/x">{label}</a>
          </div>
        )
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('format de rapport lisible', () => {
    const src = `
      export function X() {
        return <button>Download</button>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    const report = formatFindingsForReport(findings)
    assert.match(report, /\[jsx-text\]/)
    assert.match(report, /Download/)
  })
})

describe('vaultHardcodedStringsScanner — périmètre réel', () => {
  it('aucun texte hardcodé dans components/exclusive-offer/**', () => {
    const repoRoot = path.resolve(__dirname, '../../..')
    const targetDir = path.join(repoRoot, 'src/components/exclusive-offer')
    const findings = scanVaultExclusiveOfferDirectory(targetDir)
    if (findings.length > 0) {
      const report = formatFindingsForReport(findings, repoRoot)
      assert.fail(
        `Chaînes user-facing hardcodées détectées dans components/exclusive-offer/** :\n${report}\n\n` +
          `→ Solution : passer par une prop CMS (contenu module) ou par vaultCommonCta(locale, key) (libellé générique).\n` +
          `→ Si le cas est volontaire (admin/debug), ajouter au-dessus de la ligne :\n` +
          `   // i18n-allow-next-line: <raison>\n`,
      )
    }
    assert.equal(findings.length, 0)
  })
})
