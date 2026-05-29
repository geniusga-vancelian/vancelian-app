import { chromium } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const outDir = path.join(__dirname, '../.tmp-visual-check')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })

  await page.goto('http://localhost:3000/app/design', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(3000)
  await page.screenshot({ path: path.join(outDir, '01-design-showcase-top.png') })

  await page.evaluate(() => {
    document.getElementById('w4-patterns')?.scrollIntoView({ behavior: 'instant', block: 'start' })
  })
  await page.waitForTimeout(800)
  await page.screenshot({ path: path.join(outDir, '02-design-webapp4-patterns.png') })

  await page.goto('http://localhost:3000/app-ds/preview/152-balance-card.html', {
    waitUntil: 'domcontentloaded',
  })
  await page.screenshot({ path: path.join(outDir, '03-balance-card-preview.png') })

  await page.goto('http://localhost:3000/app-ds/preview/153-accounts-list.html', {
    waitUntil: 'domcontentloaded',
  })
  await page.screenshot({ path: path.join(outDir, '04-accounts-list-preview.png') })

  const dash = await page.goto('http://localhost:3000/app/dashboard', { waitUntil: 'domcontentloaded' })
  const dashUrl = page.url()
  await page.screenshot({ path: path.join(outDir, '05-dashboard-or-login.png') })

  console.log(JSON.stringify({ outDir, dashboardUrl: dashUrl, dashboardStatus: dash?.status() }))
  await browser.close()
})()
