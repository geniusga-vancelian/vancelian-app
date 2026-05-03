import assert from 'node:assert/strict'
import path from 'node:path'
import { describe, it } from 'node:test'

import {
  formatFindingsForReport,
  scanFileForHardcodedStrings,
  scanSitePublicScopes,
  SITE_SCAN_DIRS_RELATIVE,
} from '@/lib/i18n/siteHardcodedStringsScanner'

const FAKE_PATH = '/virtual/example.tsx'

describe('siteHardcodedStringsScanner — cas synthétiques', () => {
  it('détecte un texte JSX visible hardcodé', () => {
    const src = `
      export function Footer() {
        return <button>Subscribe</button>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 1)
    assert.equal(findings[0]!.kind, 'jsx-text')
    assert.equal(findings[0]!.snippet, 'Subscribe')
  })

  it('laisse passer une interpolation `{...}`', () => {
    const src = `
      export function Footer({ ctaLabel }: { ctaLabel: string }) {
        return <button>{ctaLabel}</button>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('détecte un aria-label hardcodé', () => {
    const src = `
      export function Nav() {
        return <button aria-label="Home" />
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 1)
    assert.equal(findings[0]!.kind, 'attr-aria-label')
  })

  it('respecte `// i18n-allow-next-line` au-dessus de la ligne', () => {
    const src = `
      export function Section() {
        return (
          <div>
            // i18n-allow-next-line: fallback admin debug
            <p>Section inconnue</p>
          </div>
        )
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('respecte `// i18n-allow-file` en tête de fichier', () => {
    const src = `
      // i18n-allow-file: showcase /figma uniquement, jamais rendu en prod publique
      export function Showcase() {
        return <p>Some hardcoded text</p>
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })

  it('ne signale pas les chaînes non textuelles (classes, ponctuation)', () => {
    const src = `
      export function X() {
        return (
          <div className="text-sm">
            <span>—</span>
            <a href="/projects">{label}</a>
          </div>
        )
      }
    `
    const findings = scanFileForHardcodedStrings(FAKE_PATH, src)
    assert.equal(findings.length, 0)
  })
})

describe('siteHardcodedStringsScanner — périmètre réel', () => {
  it('aucun texte hardcodé dans le périmètre site public', () => {
    const repoRoot = path.resolve(__dirname, '../../..')
    const srcDir = path.join(repoRoot, 'src')
    const findings = scanSitePublicScopes(srcDir)

    if (findings.length > 0) {
      const report = formatFindingsForReport(findings, repoRoot)
      const scopes = SITE_SCAN_DIRS_RELATIVE.map((d) => `   - src/${d}`).join('\n')
      assert.fail(
        `Chaînes user-facing hardcodées détectées dans le périmètre site public :\n${report}\n\n` +
          `Périmètres scannés :\n${scopes}\n\n` +
          `→ Solution :\n` +
          `   - texte spécifique à une section / page → prop CMS traduisible (Page + Section.dataI18n)\n` +
          `   - libellé générique d'UI                → siteCommonCta(locale, 'ma_cle')\n` +
          `→ Cas debug / admin / showcase légitime : ajouter au-dessus de la ligne :\n` +
          `     // i18n-allow-next-line: <raison>\n` +
          `  ou en tête du fichier :\n` +
          `     // i18n-allow-file: <raison>\n`,
      )
    }
    assert.equal(findings.length, 0)
  })
})
