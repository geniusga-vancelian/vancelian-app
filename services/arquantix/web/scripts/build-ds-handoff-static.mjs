#!/usr/bin/env node
/**
 * Précompile le handoff designer (JSX → JS) pour ouverture locale file://.
 *
 * Sans ce build, les *.html restent vides en double-clic : @babel/standalone
 * ne peut pas fetch les scripts externes en file:// (restriction navigateur).
 *
 * Usage:
 *   node scripts/build-ds-handoff-static.mjs
 *   node scripts/build-ds-handoff-static.mjs /chemin/vers/design_handoff_vancelian
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import { execSync } from 'node:child_process'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const WEB_ROOT = path.resolve(__dirname, '..')
const DEFAULT_HANDOFF = path.join(WEB_ROOT, '.ds-handoff/design_handoff_vancelian')

const handoffRoot = path.resolve(process.argv[2] || DEFAULT_HANDOFF)
const jsOutDir = path.join(handoffRoot, 'js')

function ensureEsbuild() {
  const require = createRequire(import.meta.url)
  try {
    return require('esbuild')
  } catch {
    execSync('npm install --no-save esbuild@0.25.0', { cwd: WEB_ROOT, stdio: 'inherit' })
    return require('esbuild')
  }
}

function compileJsx(esbuild, jsxPath) {
  const base = path.basename(jsxPath, '.jsx')
  const out = path.join(jsOutDir, `${base}.js`)
  esbuild.buildSync({
    entryPoints: [jsxPath],
    outfile: out,
    bundle: false,
    platform: 'browser',
    target: ['es2020'],
    loader: { '.jsx': 'jsx' },
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
    logLevel: 'silent',
  })
  return `${base}.js`
}

function patchHtml(htmlPath) {
  let html = fs.readFileSync(htmlPath, 'utf8')
  const name = path.basename(htmlPath)

  html = html.replace(
    /\s*<script src="https:\/\/unpkg\.com\/@babel\/standalone[^"]*"[^>]*><\/script>\s*/g,
    '\n',
  )

  html = html.replace(
    /<script type="text\/babel" src="([^"]+\.jsx)"><\/script>/g,
    (_, src) => {
      const base = path.basename(src, '.jsx')
      return `<script src="js/${base}.js"></script>`
    },
  )

  if (name === 'Wallet.html') {
    html = html.replace(
      /<script type="text\/babel">[\s\S]*?<\/script>/,
      '<script src="js/wallet-boot.js"></script>',
    )
  }

  if (!html.includes('<!-- handoff-static-build -->')) {
    html = html.replace(
      '</head>',
      '  <!-- handoff-static-build: JSX précompilé dans js/ — regénérer via scripts/build-ds-handoff-static.mjs -->\n</head>',
    )
  }

  fs.writeFileSync(htmlPath, html)
}

function writeIndex() {
  const pages = [
    ['Portfolio.html', 'Mon portefeuille'],
    ['Placer.html', 'Placer'],
    ['Marches.html', 'Marchés'],
    ['Academie.html', 'Académie'],
    ['Compte.html?id=emprunts', 'Compte — Emprunts'],
    ['Notifications.html', 'Notifications'],
    ['Profil.html', 'Profil'],
    ['Faq.html', 'FAQ'],
    ['Asset.html?sym=BTC&kind=crypto', 'Asset — BTC'],
    ['Offre.html?id=niseko', 'Offre'],
    ['Coffre.html?id=flex', 'Coffre'],
    ['Panier.html?id=top2', 'Panier'],
    ['Position.html', 'Position'],
    ['Transaction.html', 'Transaction'],
    ['Wallet.html', 'Wallet'],
  ]
  const items = pages
    .map(
      ([href, label]) =>
        `    <li><a href="${href}">${label}</a> <span class="muted">${href}</span></li>`,
    )
    .join('\n')

  fs.writeFileSync(
    path.join(handoffRoot, 'index.html'),
    `<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Vancelian — Handoff (index)</title>
  <link rel="stylesheet" href="vancelian.css" />
  <style>
    body { font-family: var(--v-font-ui, Inter, system-ui, sans-serif); background: var(--v-bg, #F7F7F4); color: var(--v-fg, #1A1815); margin: 0; padding: 32px 24px 48px; }
    h1 { font-family: var(--v-font-editorial, Georgia, serif); font-weight: 400; font-size: 2rem; margin: 0 0 8px; }
    p { color: var(--v-fg-muted, #6E665C); max-width: 42rem; line-height: 1.5; }
    ul { list-style: none; padding: 0; margin: 24px 0 0; max-width: 36rem; }
    li { padding: 10px 0; border-bottom: 1px solid var(--v-fg-10, #E2DED4); }
    a { color: var(--v-terracotta, #C0512E); text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
    .muted { color: var(--v-fg-light, #8E867A); font-size: 13px; margin-left: 8px; }
  </style>
</head>
<body>
  <h1>Vancelian — prototype statique</h1>
  <p>Pages du handoff designer. Ouvrez une entrée ci-dessous (double-clic ou lien). Les scripts JSX sont précompilés dans <code>js/</code> pour fonctionner en <code>file://</code>.</p>
  <ul>
${items}
  </ul>
</body>
</html>
`,
  )
}

function writeWalletBoot() {
  fs.writeFileSync(
    path.join(jsOutDir, 'wallet-boot.js'),
    `const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(WalletConnectView));
`,
  )
}

function main() {
  if (!fs.existsSync(path.join(handoffRoot, 'vancelian.css'))) {
    console.error(`Handoff introuvable: ${handoffRoot}`)
    process.exit(1)
  }

  fs.mkdirSync(jsOutDir, { recursive: true })
  const esbuild = ensureEsbuild()

  const jsxFiles = fs.readdirSync(handoffRoot).filter((f) => f.endsWith('.jsx'))
  for (const f of jsxFiles) {
    compileJsx(esbuild, path.join(handoffRoot, f))
    console.log(`  compiled ${f} → js/${f.replace(/\.jsx$/, '.js')}`)
  }

  writeWalletBoot()

  const htmlFiles = fs.readdirSync(handoffRoot).filter((f) => f.endsWith('.html') && f !== 'index.html')
  for (const f of htmlFiles) {
    patchHtml(path.join(handoffRoot, f))
    console.log(`  patched ${f}`)
  }

  writeIndex()
  console.log(`\nOK — ${handoffRoot}`)
  console.log('Ouvrir index.html ou une page (ex. Notifications.html) en double-clic.')
}

main()
