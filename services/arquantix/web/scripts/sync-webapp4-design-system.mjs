#!/usr/bin/env node
/**
 * Sync Webapp4 design-system zip into public/app-ds + showcase manifest.
 * Usage: node scripts/sync-webapp4-design-system.mjs "/path/to/Webapp4.zip"
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const WEB_ROOT = path.resolve(__dirname, '..')
const APP_DS = path.join(WEB_ROOT, 'public/app-ds')
const MANIFEST = path.join(WEB_ROOT, 'src/components/design-system/app/appDsShowcaseManifest.ts')

const zipPath = process.argv[2] || '/Users/gael/Downloads/Webapp4 (1).zip'
const tmpDir = path.join(WEB_ROOT, '.tmp-webapp4-ds')
const dsRoot = path.join(tmpDir, 'design-system')

/** @type {{ category: string; slug: string; title: string; desc: string; height: number }[]} */
const COMPONENTS = [
  { category: 'foundations', slug: 'colors', title: 'Couleurs', desc: 'Triade terracotta · vert anglais · bleu de Prusse', height: 520 },
  { category: 'foundations', slug: 'typography', title: 'Typographie', desc: 'Inter + Newsreader · optical sizes', height: 480 },
  { category: 'foundations', slug: 'spacing', title: 'Espacement', desc: 'Échelle 4·8·12·16·24·32·48·64', height: 360 },
  { category: 'foundations', slug: 'radii', title: 'Rayons', desc: '4 · 6 · 8 · 12 · 24 · pill', height: 320 },
  { category: 'foundations', slug: 'elevation', title: 'Élévations', desc: 'flat · subtle · medium', height: 280 },
  { category: 'foundations', slug: 'motion', title: 'Motion', desc: '120 / 200 / 320 ms · ease-out', height: 280 },
  { category: 'foundations', slug: 'iconography', title: 'Iconographie', desc: 'Kalai — 45 icônes webapp', height: 640 },
  { category: 'foundations', slug: 'logo', title: 'Logo', desc: 'Lockups noir / blanc', height: 280 },
  { category: 'primitives', slug: 'button', title: 'Button', desc: '7 variantes × 3 tailles', height: 420 },
  { category: 'primitives', slug: 'icon-button', title: 'Icon Button', desc: '40 px circulaire · topnav', height: 240 },
  { category: 'primitives', slug: 'fab', title: 'FAB', desc: '48/56 px · dark / terra / white', height: 280 },
  { category: 'primitives', slug: 'avatar', title: 'Avatar', desc: 'Initiales · icône · photo', height: 480 },
  { category: 'primitives', slug: 'avatar-exchange', title: 'Avatar Exchange', desc: 'Paire source + résultat', height: 320 },
  { category: 'primitives', slug: 'icon', title: 'Icon', desc: 'Mask CSS Kalai · currentColor', height: 360 },
  { category: 'primitives', slug: 'eyebrow', title: 'Eyebrow', desc: 'UPPERCASE · sm · tagged', height: 220 },
  { category: 'primitives', slug: 'tag', title: 'Tag', desc: 'Status success / warning / info / error', height: 320 },
  { category: 'primitives', slug: 'card', title: 'Card', desc: '.v-card · warm · grey · list', height: 360 },
  { category: 'primitives', slug: 'amount', title: 'Amount', desc: 'hero / lg / md / sm · tnum', height: 360 },
  { category: 'primitives', slug: 'net-dot', title: 'Network Dot', desc: 'Base / Ethereum / Solana', height: 200 },
  { category: 'primitives', slug: 'segmented', title: 'Segmented', desc: 'Plages 24h / 1S / 1M / 1A / Max', height: 240 },
  { category: 'app-shell', slug: 'topnav', title: 'Top Nav', desc: 'Logo · nav · wallet · réseau · search', height: 120 },
  { category: 'app-shell', slug: 'mobile-tab-bar', title: 'Mobile Tab Bar', desc: '5 onglets · safe area', height: 120 },
  { category: 'app-shell', slug: 'mobile-chain-bar', title: 'Mobile Chain Bar', desc: 'Wallet + réseau ≤960px', height: 120 },
  { category: 'app-shell', slug: 'pill-dropdown', title: 'Pill Dropdown', desc: 'Déclencheur pill + panneau .dd', height: 360 },
  { category: 'app-shell', slug: 'dropdown-menu', title: 'Dropdown Menu', desc: 'Panneau .dd · sections · items', height: 360 },
  { category: 'app-shell', slug: 'search-overlay', title: 'Search Overlay', desc: 'Plein écran · résultats groupés', height: 480 },
  { category: 'app-shell', slug: 'footer-slim', title: 'Footer Slim', desc: 'Copyright + liens utiles', height: 120 },
  { category: 'app-shell', slug: 'side-panel', title: 'Side Panel', desc: 'Drawer droit + scrim', height: 400 },
  { category: 'patterns', slug: 'section-head', title: 'Section Head', desc: 'Titre + count + voir tout · lg/md/sm', height: 320 },
  { category: 'patterns', slug: 'account-dot', title: 'Account Dot', desc: 'Avatar typé compte', height: 240 },
  { category: 'patterns', slug: 'asset-chip', title: 'Asset Chip', desc: 'Dot + label + chevron', height: 280 },
  { category: 'patterns', slug: 'money-phrase', title: 'Money Phrase', desc: 'Phrase éditoriale + montant vert', height: 200 },
  { category: 'patterns', slug: 'perf-chart', title: 'Perf Chart', desc: 'Graphique multi-plage SVG', height: 420 },
  { category: 'patterns', slug: 'balance-card', title: 'Balance Card', desc: 'Solde héro Newsreader · home produit', height: 480 },
  { category: 'patterns', slug: 'accounts-list', title: 'Accounts List', desc: '.v-card--list + .acc-row', height: 480 },
  { category: 'patterns', slug: 'news-section', title: 'News Section', desc: 'Grille actu cards', height: 520 },
  { category: 'patterns', slug: 'featured-card', title: 'Featured Card', desc: 'Offre du mois full bleed', height: 400 },
  { category: 'patterns', slug: 'advisor-portrait', title: 'Advisor — Portrait', desc: 'Photo + nom + CTA', height: 360 },
  { category: 'patterns', slug: 'advisor-banner', title: 'Advisor — Banner', desc: 'Bannière photo + headline', height: 360 },
  { category: 'patterns', slug: 'advisor-multichannel', title: 'Advisor — Multi-channel', desc: 'Téléphone · mail · chat', height: 400 },
  { category: 'patterns', slug: 'support-card', title: 'Support Card', desc: 'Sidebar compacte', height: 280 },
]

function rmrf(p) {
  if (fs.existsSync(p)) fs.rmSync(p, { recursive: true, force: true })
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true })
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name)
    const d = path.join(dest, entry.name)
    if (entry.isDirectory()) copyDir(s, d)
    else fs.copyFileSync(s, d)
  }
}

function patchCssFontPaths(content) {
  return content
    .replace(/url\("\.\/fonts\//g, 'url("/fonts/newsreader/')
    .replace(/url\('\.\/fonts\//g, "url('/fonts/newsreader/")
}

function patchPreviewHtml(html) {
  return html
    .replace(/\.\.\/\.\.\/\.\.\/vancelian\.css/g, '/app-ds/colors_and_type.css')
    .replace(/\.\.\/\.\.\/\.\.\/layout\.css/g, '/app-ds/layout.css')
    .replace(/\.\.\/\.\.\/\.\.\/preview\.css/g, '/app-ds/preview.css')
    .replace(/\.\.\/\.\.\/\.\.\/assets\//g, '/app-ds/assets/')
    .replace(/\.\.\/\.\.\/\.\.\/fonts\//g, '/fonts/newsreader/')
    .replace(/href="\.\.\/\.\.\/\.\.\/index\.html"/g, 'href="/app/design"')
}

function extractCanvasHtml(previewPath) {
  const raw = fs.readFileSync(previewPath, 'utf8')
  const canvases = [...raw.matchAll(/<div class="pv-canvas[^"]*">([\s\S]*?)<\/div>\s*(?:<div class="pv-snippet|<\/main>)/g)]
  if (canvases.length === 0) {
    const main = raw.match(/<main class="pv-stage">([\s\S]*?)<\/main>/)
    if (main) return main[1].replace(/<div class="pv-snippet[\s\S]*/g, '').trim()
    return null
  }
  return canvases.map((m) => m[1].trim()).join('\n')
}

function buildIframePreview(comp, canvasHtml, fileNum) {
  const patched = patchPreviewHtml(canvasHtml)
  return `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="/app-ds/colors_and_type.css"/>
<link rel="stylesheet" href="/app-ds/layout.css"/>
<style>
body{margin:0;padding:32px;background:var(--v-bg);font-family:var(--v-font-ui);color:var(--v-fg);min-height:100vh;}
.stage{max-width:960px;margin:0 auto;display:flex;flex-direction:column;gap:24px;}
.lbl{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--v-fg-light);margin:0 0 12px;}
</style></head>
<body><div class="stage"><p class="lbl">${comp.title} · Webapp4</p>
${patched}
</div></body></html>`
}

function slugToComponentDir(comp) {
  const map = {
    topnav: 'app-topnav',
    'footer-slim': 'app-footer-slim',
  }
  return map[comp.slug] || comp.slug
}

function generateManifestSection(startNum) {
  const groups = [
    { id: 'w4-foundations', num: '12', title: 'Webapp4 — Fondations', category: 'foundations' },
    { id: 'w4-primitives', num: '13', title: 'Webapp4 — Primitives', category: 'primitives' },
    { id: 'w4-app-shell', num: '14', title: 'Webapp4 — App shell', category: 'app-shell' },
    { id: 'w4-patterns', num: '15', title: 'Webapp4 — Patterns', category: 'patterns' },
  ]

  let n = startNum
  return groups.map((g) => {
    const items = COMPONENTS.filter((c) => c.category === g.category).map((c) => {
      const file = `${n}-${c.slug}.html`
      const openHref = `preview/${file}`
      n += 1
      return {
        title: c.title,
        file,
        height: c.height,
        openHref,
        desc: c.desc,
      }
    })
    return {
      id: g.id,
      num: g.num,
      title: g.title,
      count: `${items.length} composants · Webapp4`,
      items,
    }
  })
}

function updateManifest(sections) {
  let src = fs.readFileSync(MANIFEST, 'utf8')
  // Remove previous Webapp4 sections if re-running
  src = src.replace(/\n  \{\n    "id": "w4-foundations"[\s\S]*?\n  \}\n\]/, '\n]')
  src = src.replace(
    /export const APP_DS_SHOWCASE_VERSION = '[^']+' as const/,
    "export const APP_DS_SHOWCASE_VERSION = 'v2.4 · 28 mai 2026 · 114 + 41 Webapp4' as const",
  )

  const insert = sections
    .map(
      (sec) => `  ${JSON.stringify(sec, null, 2).replace(/\n/g, '\n  ')}`,
    )
    .join(',\n')

  src = src.replace(/\n\]/, `,\n${insert}\n]`)
  fs.writeFileSync(MANIFEST, src)
}

// --- main ---
console.log('Extracting', zipPath)
rmrf(tmpDir)
fs.mkdirSync(tmpDir, { recursive: true })
execSync(`unzip -q "${zipPath}" -d "${tmpDir}"`)

if (!fs.existsSync(path.join(dsRoot, 'vancelian.css'))) {
  console.error('Invalid zip — missing design-system/vancelian.css')
  process.exit(1)
}

// Tokens + layout
fs.writeFileSync(
  path.join(APP_DS, 'colors_and_type.css'),
  patchCssFontPaths(fs.readFileSync(path.join(dsRoot, 'vancelian.css'), 'utf8')),
)
fs.copyFileSync(path.join(dsRoot, 'layout.css'), path.join(APP_DS, 'layout.css'))
fs.copyFileSync(path.join(dsRoot, 'preview.css'), path.join(APP_DS, 'preview.css'))

// Assets
copyDir(path.join(dsRoot, 'assets'), path.join(APP_DS, 'assets'))

// Component snippets
for (const comp of COMPONENTS) {
  const srcDir = path.join(dsRoot, 'components', comp.category, comp.slug)
  const destDir = path.join(APP_DS, 'components', slugToComponentDir(comp))
  if (!fs.existsSync(srcDir)) {
    console.warn('Missing component dir:', srcDir)
    continue
  }
  fs.mkdirSync(destDir, { recursive: true })
  const snippet = path.join(srcDir, `${comp.slug}.html`)
  if (fs.existsSync(snippet)) {
    fs.copyFileSync(snippet, path.join(destDir, `${slugToComponentDir(comp)}.html`))
  }
}

// Previews
let fileNum = 119
const previewDir = path.join(APP_DS, 'preview')
fs.mkdirSync(previewDir, { recursive: true })

for (const comp of COMPONENTS) {
  const previewPath = path.join(dsRoot, 'components', comp.category, comp.slug, 'preview.html')
  const outFile = `${fileNum}-${comp.slug}.html`
  if (fs.existsSync(previewPath)) {
    const canvas = extractCanvasHtml(previewPath)
    if (canvas) {
      fs.writeFileSync(path.join(previewDir, outFile), buildIframePreview(comp, canvas, fileNum))
    } else {
      console.warn('No canvas in', previewPath)
    }
  } else {
    console.warn('No preview:', previewPath)
  }
  fileNum += 1
}

// Manifest
const w4Sections = generateManifestSection(119)
updateManifest(w4Sections)

console.log('Done — synced', COMPONENTS.length, 'Webapp4 components into public/app-ds')
console.log('Manifest updated with sections 12–15')
