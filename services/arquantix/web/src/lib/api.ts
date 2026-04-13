/**
 * FastAPI client for Arquantix
 * Replaces Strapi client
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface GlobalSettings {
  id: number
  site_name: string
  tagline: string | null
  socials_json: Record<string, any>
  seo_json: Record<string, any>
  updated_at: string
}

export interface Page {
  id: number
  slug: string
  locale: string
  title: string
  sections_json: Record<string, any>
  seo_json: Record<string, any>
  status: 'draft' | 'published'
  published_at: string | null
  updated_at: string
}

export interface News {
  id: number
  slug: string
  locale: string
  title: string
  excerpt: string | null
  content_markdown: string | null
  cover_image_url: string | null
  status: 'draft' | 'published'
  published_at: string | null
  updated_at: string
}

export interface ContactSubmission {
  id: number
  name: string
  email: string
  message: string
  ip: string | null
  user_agent: string | null
  created_at: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl
  }

  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        signal: AbortSignal.timeout(10000),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API fetch error (${url}):`, error)
      throw error
    }
  }

  // Public endpoints
  async getGlobal(): Promise<GlobalSettings> {
    return this.fetch<GlobalSettings>('/public/global')
  }

  async getPage(locale: string, slug: string): Promise<Page> {
    return this.fetch<Page>(`/public/pages/${locale}/${slug}`)
  }

  async getNewsList(locale: string, limit: number = 10): Promise<News[]> {
    return this.fetch<News[]>(`/public/news/${locale}?limit=${limit}`)
  }

  async getNews(locale: string, slug: string): Promise<News> {
    return this.fetch<News>(`/public/news/${locale}/${slug}`)
  }

  async submitContact(data: { name: string; email: string; message: string }): Promise<ContactSubmission> {
    return this.fetch<ContactSubmission>('/public/contact', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Admin endpoints (with auth)
  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    return this.fetch<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  private getAuthHeaders(token: string): HeadersInit {
    return {
      'Authorization': `Bearer ${token}`,
    }
  }

  async getGlobalAdmin(token: string): Promise<GlobalSettings> {
    return this.fetch<GlobalSettings>('/admin/global', {
      headers: this.getAuthHeaders(token),
    })
  }

  async updateGlobalAdmin(token: string, data: Partial<GlobalSettings>): Promise<GlobalSettings> {
    return this.fetch<GlobalSettings>('/admin/global', {
      method: 'PUT',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(data),
    })
  }

  async getPagesAdmin(token: string, locale?: string): Promise<Page[]> {
    const url = locale ? `/admin/pages?locale=${locale}` : '/admin/pages'
    return this.fetch<Page[]>(url, {
      headers: this.getAuthHeaders(token),
    })
  }

  async createPageAdmin(token: string, data: Partial<Page>): Promise<Page> {
    return this.fetch<Page>('/admin/pages', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(data),
    })
  }

  async updatePageAdmin(token: string, id: number, data: Partial<Page>): Promise<Page> {
    return this.fetch<Page>(`/admin/pages/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(data),
    })
  }

  async deletePageAdmin(token: string, id: number): Promise<void> {
    return this.fetch<void>(`/admin/pages/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
  }

  async getNewsAdmin(token: string, locale?: string): Promise<News[]> {
    const url = locale ? `/admin/news?locale=${locale}` : '/admin/news'
    return this.fetch<News[]>(url, {
      headers: this.getAuthHeaders(token),
    })
  }

  async createNewsAdmin(token: string, data: Partial<News>): Promise<News> {
    return this.fetch<News>('/admin/news', {
      method: 'POST',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(data),
    })
  }

  async updateNewsAdmin(token: string, id: number, data: Partial<News>): Promise<News> {
    return this.fetch<News>(`/admin/news/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(token),
      body: JSON.stringify(data),
    })
  }

  async deleteNewsAdmin(token: string, id: number): Promise<void> {
    return this.fetch<void>(`/admin/news/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(token),
    })
  }

  async getContactSubmissionsAdmin(token: string): Promise<ContactSubmission[]> {
    return this.fetch<ContactSubmission[]>('/admin/contact-submissions', {
      headers: this.getAuthHeaders(token),
    })
  }
}

export const api = new ApiClient()

