'use client'

import { Package } from 'lucide-react'

export interface ProductRegistryDraft {
  enabled: boolean
  slug: string
  productType: string
  commercialStatus: string
  visibility: string
  /** Chaîne vide = pas de rang (null côté API). */
  featuredRank: string
  categorySlug: string
  /** Virgules ou retours à la ligne. */
  tagsText: string
}

const PRODUCT_TYPES: { value: string; label: string }[] = [
  { value: 'VAULT_SIMPLE', label: 'Vault simple' },
  { value: 'EXCLUSIVE_OFFER', label: 'Offre exclusive' },
  { value: 'MANAGED_MANDATE', label: 'Mandat piloté' },
  { value: 'CRYPTO_BUNDLE', label: 'Bundle crypto' },
]

const COMMERCIAL: { value: string; label: string }[] = [
  { value: 'DRAFT', label: 'Brouillon' },
  { value: 'PUBLISHED', label: 'Publié' },
  { value: 'ARCHIVED', label: 'Archivé' },
]

const VISIBILITY: { value: string; label: string }[] = [
  { value: 'PUBLIC', label: 'Public' },
  { value: 'PRIVATE', label: 'Privé' },
  { value: 'HIDDEN', label: 'Masqué' },
]

export interface PackagedProductSettingsPanelProps {
  draft: ProductRegistryDraft
  onChange: (next: ProductRegistryDraft) => void
  /** Produit existant en base (après chargement / sauvegarde). */
  serverLinked: boolean
  /** Liaison lending active : désactivation packaged refusée côté API. */
  lendingEngineLinked: boolean
}

export function PackagedProductSettingsPanel({
  draft,
  onChange,
  serverLinked,
  lendingEngineLinked,
}: PackagedProductSettingsPanelProps) {
  const statusBanner = (() => {
    if (serverLinked) {
      return (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          <span className="font-medium">Produit packagé lié</span>
          <span className="text-emerald-800"> — entrée catalogue (Product Registry).</span>
        </div>
      )
    }
    if (draft.enabled) {
      return (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          <span className="font-medium">Brouillon catalogue</span>
          <span> — enregistrez pour créer l’entrée dans le registre.</span>
        </div>
      )
    }
    return (
      <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
        <span className="font-medium">Aucun produit packagé lié</span>
        <span> — template Vault Builder uniquement (comportement normal).</span>
      </div>
    )
  })()

  const set = (partial: Partial<ProductRegistryDraft>) => {
    onChange({ ...draft, ...partial })
  }

  return (
    <div className="border border-indigo-100 rounded-lg p-4 space-y-4 bg-indigo-50/40">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <Package className="w-4 h-4 text-indigo-600" />
          Product Settings (Product Registry)
        </h3>
      </div>

      <p className="text-xs text-gray-600">
        Métadonnées catalogue séparées du contenu CMS ci-dessous. Le slug catalogue peut différer du slug
        page si besoin.
      </p>

      {statusBanner}

      <label className="flex items-center gap-3 cursor-pointer select-none">
        <input
          type="checkbox"
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          checked={draft.enabled}
          onChange={(e) => set({ enabled: e.target.checked })}
        />
        <span className="text-sm font-medium text-gray-900">Activer comme produit packagé</span>
      </label>

      <div
        className={`space-y-3 ${!draft.enabled ? 'opacity-50 pointer-events-none' : ''}`}
        aria-hidden={!draft.enabled}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Slug catalogue</label>
            <input
              value={draft.slug}
              onChange={(e) => set({ slug: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm font-mono"
              placeholder="mon-produit"
              disabled={!draft.enabled}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Type de produit</label>
            <select
              value={draft.productType}
              onChange={(e) => set({ productType: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm"
              disabled={!draft.enabled}
            >
              {PRODUCT_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Statut commercial</label>
            <select
              value={draft.commercialStatus}
              onChange={(e) => set({ commercialStatus: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm"
              disabled={!draft.enabled}
            >
              {COMMERCIAL.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Visibilité</label>
            <select
              value={draft.visibility}
              onChange={(e) => set({ visibility: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm"
              disabled={!draft.enabled}
            >
              {VISIBILITY.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Rang mis en avant</label>
            <input
              value={draft.featuredRank}
              onChange={(e) => {
                const v = e.target.value
                if (v === '' || /^\d+$/.test(v)) set({ featuredRank: v })
              }}
              className="w-full px-3 py-2 border rounded-md text-sm"
              placeholder="vide = aucun"
              inputMode="numeric"
              disabled={!draft.enabled}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Catégorie (slug)</label>
            <input
              value={draft.categorySlug}
              onChange={(e) => set({ categorySlug: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm font-mono"
              placeholder="ex. crypto"
              disabled={!draft.enabled}
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Tags</label>
          <textarea
            value={draft.tagsText}
            onChange={(e) => set({ tagsText: e.target.value })}
            className="w-full min-h-[72px] px-3 py-2 border rounded-md text-sm font-mono"
            placeholder="virgule ou ligne : defi, premium"
            disabled={!draft.enabled}
          />
          <p className="text-xs text-gray-500 mt-1">Séparés par des virgules ou des retours à la ligne.</p>
        </div>
      </div>

      {lendingEngineLinked && (
        <p className="text-xs font-medium text-amber-800 rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
          Liaison lending active : la désactivation du produit packagé sera refusée tant que la liaison existe
          (section Moteur ci-dessous).
        </p>
      )}
    </div>
  )
}

export function buildProductRegistryDraft(
  page: { slug: string },
  packaged: {
    slug: string
    productType: string
    commercialStatus: string
    visibility: string
    featuredRank: number | null
    categorySlug: string | null
    tags: string[]
  } | null
): ProductRegistryDraft {
  if (packaged) {
    return {
      enabled: true,
      slug: packaged.slug,
      productType: packaged.productType,
      commercialStatus: packaged.commercialStatus,
      visibility: packaged.visibility,
      featuredRank: packaged.featuredRank != null ? String(packaged.featuredRank) : '',
      categorySlug: packaged.categorySlug ?? '',
      tagsText: packaged.tags.join(', '),
    }
  }
  return {
    enabled: false,
    slug: page.slug,
    productType: 'VAULT_SIMPLE',
    commercialStatus: 'DRAFT',
    visibility: 'PUBLIC',
    featuredRank: '',
    categorySlug: '',
    tagsText: '',
  }
}
