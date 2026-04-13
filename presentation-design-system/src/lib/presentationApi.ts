/**
 * Client HTTP minimal pour l'API Arquantix — decks / templates.
 * Définir VITE_ARQUANTIX_API_URL (ex. http://localhost:8000) dans .env.local
 */
const base = import.meta.env.VITE_ARQUANTIX_API_URL ?? 'http://localhost:8000';

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Réponse non JSON (${res.status}): ${text.slice(0, 200)}`);
  }
  if (!res.ok) {
    const detail = typeof data === 'object' && data && 'detail' in data ? (data as { detail: unknown }).detail : data;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data as T;
}

export type SlideTemplate = {
  id: string;
  key: string;
  name: string;
  category: string;
  description: string | null;
  status: string;
  schema_json: Record<string, unknown> | null;
  default_content_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type DeckSummary = {
  id: string;
  name: string;
  slug: string;
  deck_type: string | null;
  current_version_id: string | null;
  archived_at: string | null;
  updated_at: string;
};

export type VersionSummary = {
  id: string;
  version_number: number;
  version_label: string;
  status: string;
  is_current: boolean;
  updated_at: string;
};

export type VersionDetail = VersionSummary & {
  presentation_id: string;
  changelog: string | null;
  validated_at: string | null;
  archived_at: string | null;
  snapshot_json: Record<string, unknown> | null;
  slides: Array<{
    id: string;
    slide_template_id: string;
    template_key: string | null;
    sort_order: number;
    content_json: Record<string, unknown> | null;
    slide_title: string | null;
    subtitle: string | null;
  }>;
};

export const presentationApi = {
  baseUrl: base,

  listTemplates(params?: { search?: string; category?: string; status?: string }) {
    const q = new URLSearchParams();
    if (params?.search) q.set('search', params.search);
    if (params?.category) q.set('category', params.category);
    if (params?.status) q.set('status', params.status);
    const qs = q.toString();
    return api<SlideTemplate[]>(`/api/presentation-templates${qs ? `?${qs}` : ''}`);
  },

  listDecks(includeArchived?: boolean) {
    const q = includeArchived ? '?include_archived=true' : '';
    return api<DeckSummary[]>(`/api/presentations${q}`);
  },

  getDeck(id: string) {
    return api<DeckSummary & { description: string | null; created_at: string }>(`/api/presentations/${id}`);
  },

  createDeck(body: { name: string; slug: string; deck_type?: string; description?: string }) {
    return api<DeckSummary & { current_version_id: string | null }>('/api/presentations', {
      method: 'POST',
      body: JSON.stringify({ ...body, create_initial_version: true }),
    });
  },

  listVersions(deckId: string) {
    return api<VersionSummary[]>(`/api/presentations/${deckId}/versions`);
  },

  getVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}`);
  },

  saveDraft(versionId: string, body: { slides?: unknown[]; changelog?: string | null }) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/save-draft`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  validateVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/validate`, { method: 'POST' });
  },

  duplicateVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/duplicate`, { method: 'POST' });
  },

  archiveVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/archive`, { method: 'POST' });
  },

  restoreVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/restore`, { method: 'POST' });
  },

  setCurrentVersion(versionId: string) {
    return api<VersionDetail>(`/api/presentation-versions/${versionId}/set-current`, { method: 'POST' });
  },

  archiveTemplate(templateId: string) {
    return api<SlideTemplate>(`/api/presentation-templates/${templateId}/archive`, { method: 'POST' });
  },

  restoreTemplate(templateId: string) {
    return api<SlideTemplate>(`/api/presentation-templates/${templateId}/restore`, { method: 'POST' });
  },

  addSlide(versionId: string, slide_template_id: string, content_json?: Record<string, unknown>) {
    return api<unknown>(`/api/presentation-versions/${versionId}/slides`, {
      method: 'POST',
      body: JSON.stringify({ slide_template_id, content_json: content_json ?? {} }),
    });
  },
};
