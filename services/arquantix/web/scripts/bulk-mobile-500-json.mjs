#!/usr/bin/env node
/**
 * Normalise les réponses 500 des routes sous api/mobile/flutter :
 * { error, message } + Content-Type JSON (évite les pages HTML Next en chaîne si le handler catch).
 */
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.join(process.cwd(), 'src/app/api/mobile/flutter')

function walk(dir, acc = []) {
  for (const name of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, name.name)
    if (name.isDirectory()) walk(p, acc)
    else if (name.isFile() && name.name === 'route.ts') acc.push(p)
  }
  return acc
}

const replacement = `return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })`

const patterns = [
  [/return NextResponse\.json\(\{ error: 'Internal server error' \}, \{ status: 500 \}\)/g, replacement],
  [/return NextResponse\.json\(\{ error: 'Internal error' \}, \{ status: 500 \}\)/g, replacement],
]

let changed = 0
for (const file of walk(ROOT)) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  for (const [re, rep] of patterns) {
    s = s.replace(re, rep)
  }
  if (s !== before) {
    fs.writeFileSync(file, s)
    changed++
    console.log('updated', path.relative(process.cwd(), file))
  }
}
console.log('files updated:', changed)
