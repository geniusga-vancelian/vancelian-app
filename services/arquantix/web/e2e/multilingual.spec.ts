import { test, expect } from '@playwright/test'

/**
 * Noyau E2E multilingue — phase 2B : `/{locale}`, `/{locale}/[slug]`, legacy `/slug` → `/fr/slug`.
 */

function canonicalPath(href: string | null): string {
  if (!href) return ''
  try {
    const u = new URL(href)
    return `${u.pathname}${u.search}`
  } catch {
    return href
  }
}

test.describe('Multilingue (public)', () => {
  test('racine / redirige vers /{locale} (défaut fr sans cookie ni query)', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto('/')
    await expect(page).toHaveURL(/\/fr\/?$/)
  })

  test('racine / avec cookie en redirige vers /en', async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'arquantix-locale',
        value: 'en',
        url: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',
      },
    ])
    await page.goto('/')
    await expect(page).toHaveURL(/\/en\/?$/)
  })

  test('canonical home localisée sans ?locale= (en)', async ({ page }) => {
    await page.goto('/en')
    const href = await page.locator('link[rel="canonical"]').getAttribute('href')
    expect(href).toBeTruthy()
    expect(href).not.toContain('locale=')
    const p = canonicalPath(href)
    expect(p).not.toContain('?')
    expect(p.endsWith('/en') || p.endsWith('/en/')).toBeTruthy()
  })

  test('legacy /e2e-smoke → /fr/e2e-smoke (308)', async ({ page }) => {
    await page.goto('/e2e-smoke')
    await expect(page).toHaveURL(/\/fr\/e2e-smoke/)
  })

  test('CMS localisé : canonical sans ?locale= sur /fr/e2e-smoke', async ({ page }) => {
    await page.goto('/fr/e2e-smoke')
    const href = await page.locator('link[rel="canonical"]').getAttribute('href')
    expect(href).toBeTruthy()
    expect(href).not.toContain('locale=')
    const p = canonicalPath(href)
    expect(p).not.toContain('?')
    expect(p).toContain('/fr/e2e-smoke')
  })

  test('CMS localisé : si hreflang présents, URLs sans ?locale= (e2e-smoke)', async ({ page }) => {
    await page.goto('/fr/e2e-smoke')
    const alts = page.locator('link[rel="alternate"][hreflang]')
    const count = await alts.count()
    for (let i = 0; i < count; i++) {
      const h = await alts.nth(i).getAttribute('href')
      expect(h).toBeTruthy()
      expect(h).not.toContain('locale=')
      expect(h).not.toContain('?locale')
    }
  })

  test('/en/e2e-smoke : canonical et hreflang sans ?locale= (si page servie)', async ({
    page,
  }) => {
    const resp = await page.goto('/en/e2e-smoke')
    if (resp?.status() === 404) {
      test.skip()
      return
    }
    const canonical = await page.locator('link[rel="canonical"]').getAttribute('href')
    expect(canonical).toBeTruthy()
    expect(canonical).not.toContain('locale=')
    const n = await page.locator('link[rel="alternate"][hreflang]').count()
    if (n === 0) return
    for (let i = 0; i < n; i++) {
      const h = await page.locator('link[rel="alternate"][hreflang]').nth(i).getAttribute('href')
      expect(h).toBeTruthy()
      expect(h).not.toContain('locale=')
    }
  })

  test('/en/e2e-smoke : html lang=en même si cookie fr', async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'arquantix-locale',
        value: 'fr',
        url: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',
      },
    ])
    await page.goto('/en/e2e-smoke')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('/en : html lang=en même si cookie fr (URL prioritaire)', async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'arquantix-locale',
        value: 'fr',
        url: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',
      },
    ])
    await page.goto('/en')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('/en : og:locale en_US', async ({ page }) => {
    await page.goto('/en')
    await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en_US')
  })

  test('sans cookie, /?locale=en redirige vers /en puis html lang=en', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto('/?locale=en')
    await expect(page).toHaveURL(/\/en\/?$/)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en_US')
  })

  test('locale query invalide sur / → fallback /fr', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto('/?locale=xx')
    await expect(page).toHaveURL(/\/fr\/?$/)
  })

  test('footer : cookie en sur / → redirection /en → copyright EN (seed)', async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'arquantix-locale',
        value: 'en',
        url: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',
      },
    ])
    await page.goto('/')
    await expect(page).toHaveURL(/\/en/)
    await expect(page.getByTestId('site-footer')).toContainText('E2E-FOOTER-EN')
  })

  test('footer : /fr sans cookie → copyright FR (seed)', async ({ page, context }) => {
    await context.clearCookies()
    await page.goto('/fr')
    await expect(page.getByTestId('site-footer')).toContainText('E2E-FOOTER-FR')
  })
})
