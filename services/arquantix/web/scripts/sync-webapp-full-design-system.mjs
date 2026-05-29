#!/usr/bin/env node
/**
 * Sync Webapp-full.zip (design_handoff_vancelian) into public/app-ds + app styles + showcase.
 * Usage: node scripts/sync-webapp-full-design-system.mjs "/path/to/Webapp-full.zip"
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const WEB_ROOT = path.resolve(__dirname, '..')
const HANDOFF_DIR = 'design_handoff_vancelian'
const APP_DS = path.join(WEB_ROOT, 'public/app-ds')
const STYLES_APP = path.join(WEB_ROOT, 'src/styles/app')
const COMPONENTS_CSS = path.join(STYLES_APP, 'vancelian-app-components.css')
const MANIFEST = path.join(WEB_ROOT, 'src/components/design-system/app/appDsShowcaseManifest.ts')

const zipPath = process.argv[2] || '/Users/gael/Downloads/Webapp-full.zip'
const tmpDir = path.join(WEB_ROOT, '.tmp-webapp-full-ds')

/** @type {{ slug: string; title: string; desc: string; height: number; canvas: string; extraCss?: string }[]} */
const WFULL_COMPONENTS = [
  {
    slug: 'avatar-safran',
    title: 'Account dot — variante safran',
    desc: 'Cryptos · Managed Portfolio = blue · safran',
    height: 200,
    canvas: `<div class="pv-row">
      <span class="avt avt--safran">CR</span>
      <span class="avt avt--blue">MP</span>
      <span class="avt avt--green">EP</span>
      <span class="avt avt--terra">OF</span>
    </div>`,
  },
  {
    slug: 'borrow-cta',
    title: 'Borrow CTA — avance de liquidité',
    desc: 'Carte CTA page Emprunts · powered by Morpho',
    height: 320,
    canvas: `<div class="v-card brw-cta">
      <div class="brw-cta__body">
        <h3 class="brw-cta__title">Avance de liquidité</h3>
        <p class="brw-cta__lead">Empruntez des USDC en garantissant vos cryptos — sans les vendre.</p>
        <p class="brw-cta__powered">
          <span class="brw-cta__powered-lbl">Propulsé par</span>
          <span class="brw-cta__powered-name">Morpho</span>
        </p>
      </div>
      <button type="button" class="btn btn--primary btn--lg brw-cta__btn">Demander une avance</button>
    </div>`,
    extraCss: '/app-ds/borrow-layout-patterns.css',
  },
  {
    slug: 'loan-card',
    title: 'Loan card — emprunt actif',
    desc: 'Carte cliquable · stats · barre d’utilisation',
    height: 480,
    canvas: `<a class="v-card loan" href="#">
      <header class="loan__head">
        <span class="loan__coin"><img src="/app-ds/assets/crypto/btc.svg" alt="" /></span>
        <div class="loan__title-block">
          <h4 class="loan__title">Garantie Bitcoin</h4>
          <p class="loan__sub v-tnum">0,42 cbBTC en garantie</p>
        </div>
        <span class="loan__chv" aria-hidden="true">›</span>
      </header>
      <dl class="loan__stats">
        <div class="loan__row"><dt>Montant emprunté</dt><dd class="v-tnum">12 480,00 USDC</dd></div>
        <div class="loan__row"><dt>Niveau de sécurité</dt><dd><span class="loan__safety" style="color:var(--v-green);background:var(--v-success-bg)"><span class="loan__safety-dot" style="background:var(--v-green)"></span>Sain</span></dd></div>
        <div class="loan__row"><dt>Utilisation actuelle</dt><dd class="v-tnum"><span class="loan__usage"><span class="loan__usage-bar"><span class="loan__usage-fill" style="width:42%;background:var(--v-green)"></span></span><span>42 %</span></span></dd></div>
        <div class="loan__row"><dt>Taux d'intérêt</dt><dd class="v-tnum">4,2 % variable</dd></div>
      </dl>
    </a>`,
    extraCss: '/app-ds/borrow-layout-patterns.css',
  },
  {
    slug: 'mobile-sticky-bar',
    title: 'Mobile sticky bar — .mstick',
    desc: 'CTA fixe au-dessus du tab bar · gain % + bouton',
    height: 120,
    canvas: `<div class="mstick" style="display:block;position:relative;bottom:auto">
      <div class="mstick__inner">
        <div class="mstick__meta">
          <span class="mstick__k mstick__k--gain">+ 7,2 %</span>
          <span class="mstick__sub">Sur 1 an</span>
        </div>
        <div class="mstick__cta"><button type="button" class="btn btn--primary">Investir</button></div>
      </div>
    </div>`,
  },
  {
    slug: 'borrow-explainer',
    title: 'Borrow explainer — 3 points',
    desc: 'Garantie · intérêt · remboursement libre',
    height: 420,
    canvas: `<div class="brw-explain">
      <h3 class="brw-explain__title">Comment ça marche</h3>
      <div class="brw-explain__points">
        <div class="brw-explain__point"><span class="brw-explain__ico">🔒</span><div class="brw-explain__text"><p class="brw-explain__pt-title">Vos cryptos restent en garantie</p><p class="brw-explain__pt-body">Vous ne vendez rien.</p></div></div>
        <div class="brw-explain__point"><span class="brw-explain__ico">↗</span><div class="brw-explain__text"><p class="brw-explain__pt-title">Un intérêt qui rembourse</p><p class="brw-explain__pt-body">La dette diminue au fil du temps.</p></div></div>
      </div>
    </div>`,
    extraCss: '/app-ds/borrow-layout-patterns.css',
  },
  {
    slug: 'actu-photo-zoom',
    title: 'Actu card — zoom photo au survol',
    desc: 'Image scale 1.05 · chip texte fixe',
    height: 360,
    canvas: `<a class="actu" href="#" style="max-width:320px;text-decoration:none;color:inherit">
      <div class="actu__img">
        <span class="actu__cat"><span class="cchip"><span class="cdot"></span>Immobilier</span></span>
      </div>
      <h3 class="actu__title">Résidence Niseko — ouverture Q4</h3>
      <p class="actu__meta">Il y a 2 jours</p>
    </a>`,
  },
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

function patchAvtSafran(css) {
  if (css.includes('.avt--safran')) return css
  return css.replace(
    /\.avt--warm\s*\{[^}]+\}/,
    (m) =>
      `${m}\n.avt--safran { background: var(--v-yellow);      color: #FFFFFF; }`,
  ).replace(
    /\.avt:not\(\.avt--terra\):not\(\.avt--green\):not\(\.avt--blue\):not\(\.avt--dark\)/,
    '.avt:not(.avt--terra):not(.avt--green):not(.avt--blue):not(.avt--dark):not(.avt--safran)',
  )
}

function buildPreviewHtml(comp, fileNum) {
  const extraLink = comp.extraCss
    ? `<link rel="stylesheet" href="${comp.extraCss}"/>`
    : ''
  return `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="/app-ds/colors_and_type.css"/>
<link rel="stylesheet" href="/app-ds/layout.css"/>
${extraLink}
<style>
body{margin:0;padding:32px;background:var(--v-bg);font-family:var(--v-font-ui);color:var(--v-fg);min-height:100vh;}
.stage{max-width:960px;margin:0 auto;display:flex;flex-direction:column;gap:24px;}
.lbl{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--v-fg-light);margin:0 0 12px;}
</style></head>
<body><div class="stage"><p class="lbl">${comp.title} · Webapp-full</p>
${comp.canvas}
</div></body></html>`
}

function extractBorrowCss(handoffRoot) {
  const lines = fs.readFileSync(path.join(handoffRoot, 'category-detail.css'), 'utf8').split('\n')
  const body = lines.slice(218, 580).join('\n')
  return `/* Synced from Webapp-full — category-detail.css (L219–580) */\n${body}\n`
}

function patchLayoutAssetPaths(content) {
  return content.replace(/url\('assets\//g, "url('/app-ds/assets/")
}

function updateManifest(sections) {
  let src = fs.readFileSync(MANIFEST, 'utf8')
  src = src.replace(/\n  \{\n    "id": "w-full"[\s\S]*?\n  \}\n\]/, '\n]')
  src = src.replace(
    /export const APP_DS_SHOWCASE_VERSION = '[^']+' as const/,
    "export const APP_DS_SHOWCASE_VERSION = 'v2.5 · 29 mai 2026 · 114 + 41 Webapp4 + 6 Webapp-full' as const",
  )
  const insert = sections
    .map((sec) => `  ${JSON.stringify(sec, null, 2).replace(/\n/g, '\n  ')}`)
    .join(',\n')
  fs.writeFileSync(MANIFEST, src.replace(/\n\]/, `,\n${insert}\n]`))
}

function patchAvatarPreview() {
  const p = path.join(APP_DS, 'preview/130-avatar.html')
  if (!fs.existsSync(p)) return
  let html = fs.readFileSync(p, 'utf8')
  if (html.includes('avt--safran')) return
  html = html.replace(
    '<span class="avt avt--warm">VW</span>',
    '<span class="avt avt--warm">VW</span>\n          <span class="avt avt--safran">CR</span>',
  )
  fs.writeFileSync(p, html)
}

function generateManifestSection(startNum) {
  let n = startNum
  const items = WFULL_COMPONENTS.map((c) => {
    const file = `${n}-${c.slug}.html`
    const openHref = `preview/${file}`
    n += 1
    return { title: c.title, file, height: c.height, openHref, desc: c.desc }
  })
  return {
    id: 'w-full',
    num: '16',
    title: 'Webapp-full — Patterns produit',
    count: `${items.length} composants · Webapp-full (mai 2026)`,
    items,
  }
}

// --- main ---
console.log('Extracting', zipPath)
rmrf(tmpDir)
fs.mkdirSync(tmpDir, { recursive: true })
execSync(`unzip -q "${zipPath}" -d "${tmpDir}"`)

const handoffRoot = path.join(tmpDir, HANDOFF_DIR)
if (!fs.existsSync(path.join(handoffRoot, 'vancelian.css'))) {
  console.error('Invalid zip — missing', HANDOFF_DIR)
  process.exit(1)
}

// Tokens + layout
fs.writeFileSync(
  path.join(APP_DS, 'colors_and_type.css'),
  patchCssFontPaths(fs.readFileSync(path.join(handoffRoot, 'vancelian.css'), 'utf8')),
)
fs.writeFileSync(
  path.join(APP_DS, 'layout.css'),
  patchLayoutAssetPaths(fs.readFileSync(path.join(handoffRoot, 'layout.css'), 'utf8')),
)

// Borrow patterns (public + scoped app)
const borrowCss = extractBorrowCss(handoffRoot)
fs.writeFileSync(path.join(APP_DS, 'borrow-layout-patterns.css'), borrowCss)
fs.writeFileSync(
  path.join(STYLES_APP, 'borrow-layout-patterns.css'),
  `@scope ([data-v-ds='app']) {\n${borrowCss}\n}\n`,
)

// Assets
copyDir(path.join(handoffRoot, 'assets'), path.join(APP_DS, 'assets'))

// Component CSS patch (avt--safran)
let compCss = fs.readFileSync(COMPONENTS_CSS, 'utf8')
compCss = patchAvtSafran(compCss)
fs.writeFileSync(COMPONENTS_CSS, compCss)

// Previews
let fileNum = 160
const previewDir = path.join(APP_DS, 'preview')
fs.mkdirSync(previewDir, { recursive: true })
for (const comp of WFULL_COMPONENTS) {
  fs.writeFileSync(
    path.join(previewDir, `${fileNum}-${comp.slug}.html`),
    buildPreviewHtml(comp, fileNum),
  )
  fileNum += 1
}

patchAvatarPreview()
updateManifest([generateManifestSection(160)])

console.log('Done — Webapp-full synced:', WFULL_COMPONENTS.length, 'previews + tokens + layout + borrow CSS')
