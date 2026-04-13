// Stub for Strapi integration (not used)
// This file exists to prevent build errors for pages that import it but are not actively used

export interface StrapiGlobal {
  branding?: { name?: string; tagline?: string }
}

export interface StrapiPage {
  title: string
}

export interface StrapiNewsItem {
  id: number
  title: string
  excerpt: string
  published_at: string
}

export const api = {
  async getGlobal(): Promise<StrapiGlobal | null> {
    return null
  },
  async getPages(_locale: string, _slug: string): Promise<StrapiPage[]> {
    return []
  },
  async getNews(_locale?: string, _limit?: number): Promise<StrapiNewsItem[]> {
    return []
  },
  async submitContact(_data: unknown) {
    return Promise.resolve()
  },
}
