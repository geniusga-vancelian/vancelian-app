'use client'

import { useEffect, useState } from 'react'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { MediaField } from './MediaField'
import { ExclusiveOfferSelector } from './ExclusiveOfferSelector'
import { ConfirmDialog } from './ConfirmDialog'
import { readShowAllExclusiveOffersFlag } from '@/lib/cms/showAllExclusiveOffersFlag'

/** Modules communs : formulaire « Apparence » vs « Textes » (évite de dupliquer les champs traduits). */
export type CommonModuleEditorSplit = 'design' | 'locale'

interface SectionEditorProps {
  sectionKey: string
  data: any
  onChange: (data: any) => void
  /** Si défini (édition module commun), ne montre qu’un sous-ensemble de champs selon l’onglet actif. */
  commonModuleSplit?: CommonModuleEditorSplit
}

/**
 * Section-specific editor components
 * Provides structured editing based on section type
 */
export function SectionEditor({
  sectionKey,
  data,
  onChange,
  commonModuleSplit,
}: SectionEditorProps) {
  /** Évite les non-match si la clé Prisma / API contient des espaces parasites. */
  const sk = typeof sectionKey === 'string' ? sectionKey.trim() : sectionKey
  /** `cta_2`, `project_grid_3`, … → type de base pour choisir le formulaire. */
  const canonical = resolveCanonicalSectionKey(sk) ?? sk

  const updateField = (path: string, value: any) => {
    const keys = path.split('.')
    const newData = { ...data }
    let current: any = newData

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i]
      if (!(key in current) || typeof current[key] !== 'object' || current[key] === null) {
        current[key] = {}
      }
      current = current[key]
    }

    current[keys[keys.length - 1]] = value
    onChange(newData)
  }

  // Hero Homepage + Hero Secondary (même schéma de données)
  if (sk === 'hero' || sk === 'hero_secondary') {
    const isSecondary = sk === 'hero_secondary'
    const opacityPct = Math.round(
      Math.min(100, Math.max(0, (data.backgroundImageOpacity ?? 1) * 100)),
    )
    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {isSecondary
              ? 'Titre (2 lignes : page secondaire — typo DS, 2ᵉ ligne sans dégradé)'
              : 'Titre (2 lignes : 1ʳᵉ ligne noir, 2ᵉ ligne dégradé rose → or)'}
          </label>
          <textarea
            value={data.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            rows={3}
            placeholder={
              isSecondary
                ? 'Titre de la page,\ndeuxième ligne'
                : 'Rendement immobilier premium,\nlivré on-chain.'
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-sans text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Sous-titre
          </label>
          <textarea
            value={data.subtitle || ''}
            onChange={(e) => updateField('subtitle', e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Texte latéral / complément (optionnel)
          </label>
          <textarea
            value={data.sidebarText || ''}
            onChange={(e) => updateField('sidebarText', e.target.value)}
            rows={4}
            placeholder="Bloc texte additionnel fusionné au corps du hero sur le site public (traduisible)."
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-sans text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide si non utilisé. Même champ pour hero d’accueil et hero secondaire.
          </p>
        </div>

        <div>
          <MediaField
            value={data.backgroundMediaId || null}
            onChange={(mediaId) => updateField('backgroundMediaId', mediaId)}
            label="Image de fond (optionnelle, très légère)"
            allowClear={true}
            preview={true}
          />
          {isSecondary ? (
            <p className="mt-2 text-xs text-gray-500">
              Avec image : texte et pastilles en contraste clair sur la photo (même rendu que le hero
              offre exclusive). Sans image : fond blanc, texte noir.
            </p>
          ) : null}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Opacité de l’image de fond ({opacityPct}%)
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={opacityPct}
            onChange={(e) =>
              updateField('backgroundImageOpacity', parseInt(e.target.value, 10) / 100)
            }
            className="w-full accent-indigo-600"
          />
          <p className="mt-1 text-xs text-gray-500">
            {isSecondary
              ? '0 % = image invisible. Avec opacité sous 100 % et image : voile clair pour la lisibilité (sans mode contraste photo).'
              : '0 % = image invisible (le dégradé de lisibilité reste appliqué par-dessus).'}
          </p>
        </div>

        {isSecondary ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pastilles sous le titre (une par ligne)
            </label>
            <textarea
              value={Array.isArray(data.tags) ? data.tags.join('\n') : ''}
              onChange={(e) => {
                const lines = e.target.value
                  .split('\n')
                  .map((s) => s.trim())
                  .filter((s) => s.length > 0)
                updateField('tags', lines.length > 0 ? lines : undefined)
              }}
              rows={4}
              placeholder={'Pastille 1\nPastille 2'}
              className="w-full rounded-md border border-gray-300 px-3 py-2 font-sans text-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        ) : null}

        {/* `hideCta` est lu par `SectionHero` pour les deux variantes ; exposé ici
            sur le hero principal aussi pour cohérence d'UI (audit U3). */}
        <div className="flex items-center gap-2">
          <input
            id={`hero-${isSecondary ? 'secondary' : 'homepage'}-hide-cta`}
            type="checkbox"
            checked={Boolean(data.hideCta)}
            onChange={(e) => updateField('hideCta', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label
            htmlFor={`hero-${isSecondary ? 'secondary' : 'homepage'}-hide-cta`}
            className="text-sm text-gray-700"
          >
            Masquer le bouton CTA (hero titre + sous-titre seuls)
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Texte du bouton CTA
          </label>
          <input
            type="text"
            value={data.ctaText || ''}
            onChange={(e) => updateField('ctaText', e.target.value)}
            placeholder="ex. Découvrir nos offres"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Lien du bouton CTA
          </label>
          <input
            type="text"
            value={data.ctaLink || ''}
            onChange={(e) => updateField('ctaLink', e.target.value)}
            placeholder="ex. /fr/contact"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        {isSecondary ? (
          <p className="text-xs text-gray-500">
            Hero Secondary : pas de KPI ni de bloc email sur le site public.
          </p>
        ) : (
          <p className="text-xs text-gray-500">
            Hero homepage : pas de bandeau KPI ni de champ email (retirés du rendu).
          </p>
        )}
      </div>
    )
  }

  // Projects section editor (offres exclusives Vault Builder + champs éditoriaux)
  if (canonical === 'project_grid') {
    return (
      <div className="space-y-4">
        {/* En-tête de section : convention Surtitre / Titre / Description.
            Tous les 3 champs sont optionnels et traduisibles
            (cf. `SECTION_I18N_POLICIES['project_grid']`). */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow || ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. EXCLUSIVE OFFERS"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Titre
          </label>
          <input
            type="text"
            value={data.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Nos offres exclusives"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Grand titre affiché au-dessus de la grille. Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={data.description || ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="ex. Une sélection de projets immobiliers réservée à nos membres."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre max d’offres affichées
          </label>
          <input
            type="number"
            min="1"
            max="20"
            value={data.limit || 3}
            onChange={(e) => updateField('limit', parseInt(e.target.value, 10) || 3)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div className="flex items-start gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
          <input
            id="showAllExclusiveOffers"
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            checked={readShowAllExclusiveOffersFlag(data.showAllExclusiveOffers)}
            onChange={(e) => updateField('showAllExclusiveOffers', e.target.checked)}
          />
          <label htmlFor="showAllExclusiveOffers" className="text-sm text-gray-800">
            <span className="font-medium">Toutes les offres (sans sélection)</span>
            <span className="block text-gray-600 font-normal mt-0.5">
              Affiche les offres exclusives publiées, des plus récentes aux plus anciennes (selon le
              nombre max ci-dessus). La sélection manuelle ci-dessous est ignorée.
            </span>
          </label>
        </div>

        {readShowAllExclusiveOffersFlag(data.showAllExclusiveOffers) !== true && (
          <div>
            <ExclusiveOfferSelector
              selectedPackagedProductIds={data.selectedPackagedProductIds || []}
              onChange={(ids) => updateField('selectedPackagedProductIds', ids)}
              limit={data.limit || 3}
            />
            <p className="text-xs text-gray-500 mt-1">
              Cartes = offres exclusives (Vault Builder). Si la liste exclusive est vide mais que
              d’anciens selectedProjectIds existent en base, le site peut encore afficher les anciens projets.
            </p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Libellé du bouton « voir toutes les offres »
          </label>
          <input
            type="text"
            value={data.viewAllButtonText || ''}
            onChange={(e) => updateField('viewAllButtonText', e.target.value)}
            placeholder="Laisser vide pour utiliser le libellé par défaut traduit"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Si vide, le site affiche un libellé traduit par défaut (FR/EN/IT).
          </p>
        </div>
      </div>
    )
  }

  // Grille de points forts (même mapping que `features` / `about` → SectionAbout)
  if (canonical === 'feature_grid') {
    const items: Array<{ title: string; description: string }> = Array.isArray(data.items)
      ? data.items
      : []

    const setItems = (next: typeof items) => updateField('items', next)

    const updateItem = (index: number, field: 'title' | 'description', value: string) => {
      const next = [...items]
      if (!next[index]) next[index] = { title: '', description: '' }
      next[index] = { ...next[index], [field]: value }
      setItems(next)
    }

    const addItem = () => setItems([...items, { title: '', description: '' }])
    const removeItem = (index: number) => setItems(items.filter((_, i) => i !== index))
    const moveItem = (index: number, direction: 'up' | 'down') => {
      const target = direction === 'up' ? index - 1 : index + 1
      if (target < 0 || target >= items.length) return
      const next = [...items]
      ;[next[index], next[target]] = [next[target], next[index]]
      setItems(next)
    }

    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Bloc liste + visuel optionnel (checklist Figma). Pas de surtitre séparé : seuls titre, textes
          d’introduction et points sont exposés ici.
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Titre</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Pourquoi nous choisir"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Champ traduisible.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description <span className="text-gray-500 font-normal">(chapô)</span>
          </label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="Court paragraphe sous le titre."
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Champ traduisible.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Contenu complémentaire <span className="text-gray-500 font-normal">(optionnel)</span>
          </label>
          <textarea
            value={data.content ?? ''}
            onChange={(e) => updateField('content', e.target.value)}
            rows={3}
            placeholder="Texte additionnel fusionné sous la description sur le site public."
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Champ traduisible.</p>
        </div>
        <div>
          <MediaField
            value={data.imageMediaId || null}
            onChange={(mediaId) => updateField('imageMediaId', mediaId)}
            label="Image (médiathèque)"
            allowClear={true}
            preview={true}
          />
          <p className="mt-1 text-xs text-gray-500">
            Une ancienne URL saisie dans le JSON brut (<code className="rounded bg-gray-100 px-1">imageUrl</code>)
            reste prise en compte si aucun média n’est sélectionné.
          </p>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Points forts ({items.length})</span>
          <button
            type="button"
            onClick={addItem}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            + Ajouter un point
          </button>
        </div>
        {items.length === 0 ? (
          <p className="rounded-md border border-dashed border-gray-200 py-6 text-center text-sm text-gray-500">
            Aucun point — le bloc n’affichera que le texte et l’image si présents.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => (
              <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-gray-500">Point {index + 1}</span>
                  <div className="flex gap-2">
                    {index > 0 ? (
                      <button
                        type="button"
                        className="text-sm text-gray-600 hover:text-gray-900"
                        onClick={() => moveItem(index, 'up')}
                      >
                        ↑
                      </button>
                    ) : null}
                    {index < items.length - 1 ? (
                      <button
                        type="button"
                        className="text-sm text-gray-600 hover:text-gray-900"
                        onClick={() => moveItem(index, 'down')}
                      >
                        ↓
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="text-sm text-red-600 hover:text-red-800"
                      onClick={() => removeItem(index)}
                    >
                      Retirer
                    </button>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Titre du point</label>
                    <input
                      type="text"
                      value={item.title ?? ''}
                      onChange={(e) => updateItem(index, 'title', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="mb-1 block text-xs font-medium text-gray-700">Description</label>
                    <textarea
                      value={item.description ?? ''}
                      onChange={(e) => updateItem(index, 'description', e.target.value)}
                      rows={2}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // FAQ section editor
  if (canonical === 'faq') {
    const items = data.items || []
    const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

    const generateId = () => {
      return `faq-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }

    const addItem = () => {
      const newItem = {
        id: generateId(),
        question: '',
        answerMarkdown: '',
      }
      updateField('items', [...items, newItem])
    }

    const removeItem = (id: string) => {
      updateField(
        'items',
        items.filter((item: any) => item.id !== id)
      )
      setDeleteConfirm(null)
    }

    const updateItem = (id: string, field: 'question' | 'answerMarkdown', value: string) => {
      updateField(
        'items',
        items.map((item: any) => (item.id === id ? { ...item, [field]: value } : item))
      )
    }

    const moveItem = (index: number, direction: 'up' | 'down') => {
      const newItems = [...items]
      const targetIndex = direction === 'up' ? index - 1 : index + 1
      if (targetIndex >= 0 && targetIndex < newItems.length) {
        ;[newItems[index], newItems[targetIndex]] = [newItems[targetIndex], newItems[index]]
        updateField('items', newItems)
      }
    }

    // Compat douce : si un contenu legacy a un titre encore dans `subtitle`
    // (ancien emplacement), on l'affiche en placeholder sous le champ « Titre »
    // pour signaler à l'opérateur ce qui s'affiche actuellement sur le site
    // sans réécrire automatiquement la donnée. Le mapping renderer fait
    // `title || subtitle` (cf. `SectionRenderer.faq`) donc le site reste
    // identique tant que l'opérateur n'a pas migré explicitement.
    const hasLegacySubtitle =
      typeof data.subtitle === 'string' &&
      data.subtitle.trim() !== '' &&
      (typeof data.title !== 'string' || data.title.trim() === '')

    return (
      <div className="space-y-4">
        {/* En-tête de section : convention Surtitre / Titre / Description
            (cf. `media_text`, `figma_testimonial_cards`, `key_figures`…).
            Tous les 3 champs sont optionnels et traduisibles
            (cf. `SECTION_I18N_POLICIES['faq']`). */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. FAQ"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Titre
          </label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder={
              hasLegacySubtitle
                ? `Actuellement affiché sur le site : « ${String(data.subtitle).trim()} » (legacy)`
                : 'ex. Questions Fréquentes.'
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Grand titre affiché au-dessus des questions. Champ traduisible.
            {hasLegacySubtitle ? (
              <>
                {' '}Un titre est encore stocké dans l&rsquo;ancien champ{' '}
                <code className="rounded bg-gray-100 px-1">subtitle</code>{' '}
                et continue de s&rsquo;afficher tant que ce champ « Titre » est vide.
              </>
            ) : null}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="ex. Tout ce qu'il faut savoir avant de se lancer."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>

        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50/80 p-4">
          <p className="text-sm font-medium text-gray-800">Accordéon — tout ouvrir / tout replier</p>
          <p className="text-xs text-gray-600">
            Libellés optionnels des boutons globaux au-dessus de la liste. Laisser vide pour masquer les
            contrôles. Champs traduisibles.
          </p>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Libellé « tout développer »
            </label>
            <input
              type="text"
              value={
                data.ui != null &&
                typeof data.ui === 'object' &&
                !Array.isArray(data.ui) &&
                typeof (data.ui as { expandAllLabel?: string }).expandAllLabel === 'string'
                  ? (data.ui as { expandAllLabel: string }).expandAllLabel
                  : ''
              }
              onChange={(e) => updateField('ui.expandAllLabel', e.target.value)}
              placeholder="ex. Tout afficher"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Libellé « tout replier »
            </label>
            <input
              type="text"
              value={
                data.ui != null &&
                typeof data.ui === 'object' &&
                !Array.isArray(data.ui) &&
                typeof (data.ui as { collapseAllLabel?: string }).collapseAllLabel === 'string'
                  ? (data.ui as { collapseAllLabel: string }).collapseAllLabel
                  : ''
              }
              onChange={(e) => updateField('ui.collapseAllLabel', e.target.value)}
              placeholder="ex. Tout masquer"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Questions et réponses
            </label>
            <button
              type="button"
              onClick={addItem}
              className="px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              + Ajouter une question
            </button>
          </div>

          {items.length === 0 ? (
            <p className="text-sm text-gray-500 py-4 text-center border border-gray-200 rounded-md">
              Aucune question pour l’instant. Cliquez sur « Ajouter une question » pour commencer.
            </p>
          ) : (
            <div className="space-y-4">
              {items.map((item: any, index: number) => (
                <div
                  key={item.id}
                  className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                >
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-xs font-medium text-gray-500">
                      Question {index + 1}
                    </span>
                    <div className="flex gap-2">
                      {index > 0 && (
                        <button
                          type="button"
                          onClick={() => moveItem(index, 'up')}
                          className="text-gray-600 hover:text-gray-900 text-sm"
                          title="Monter"
                        >
                          ↑
                        </button>
                      )}
                      {index < items.length - 1 && (
                        <button
                          type="button"
                          onClick={() => moveItem(index, 'down')}
                          className="text-gray-600 hover:text-gray-900 text-sm"
                          title="Descendre"
                        >
                          ↓
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setDeleteConfirm(item.id)}
                        className="text-red-600 hover:text-red-900 text-sm"
                        title="Retirer"
                      >
                        Retirer
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Question
                      </label>
                      <input
                        type="text"
                        value={item.question || ''}
                        onChange={(e) => updateItem(item.id, 'question', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                        placeholder="ex. Comment souscrire à une offre ?"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Réponse <span className="text-gray-500 font-normal">(Markdown)</span>
                      </label>
                      <textarea
                        value={item.answerMarkdown || ''}
                        onChange={(e) => updateItem(item.id, 'answerMarkdown', e.target.value)}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
                        placeholder="Saisir la réponse en Markdown…"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Prise en charge Markdown : **gras**, *italique*, liens, listes, etc.
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <ConfirmDialog
          open={deleteConfirm !== null}
          onOpenChange={(open) => !open && setDeleteConfirm(null)}
          title="Retirer cette question"
          description="Supprimer cette entrée de la FAQ ? Cette action ne peut pas être annulée."
          confirmLabel="Supprimer"
          cancelLabel="Annuler"
          onConfirm={() => { deleteConfirm && removeItem(deleteConfirm) }}
        />
      </div>
    )
  }

  // How it works (étapes + CTA)
  if (canonical === 'how_it_works') {
    const steps = Array.isArray(data.steps) ? data.steps : []
    const hideStepNumbering = data.hideStepNumbering === true

    const updateStep = (
      index: number,
      field:
        | 'number'
        | 'title'
        | 'description'
        | 'imageMediaId'
        | 'stepButtonLabel'
        | 'stepButtonHref',
      value: string | null,
    ) => {
      const next = steps.map((s: Record<string, unknown>, i: number) => {
        if (i !== index) return { ...s }
        if (field === 'imageMediaId') {
          if (value === null || value === '') {
            const { imageMediaId: _drop, ...rest } = s
            return rest
          }
          return { ...s, imageMediaId: value }
        }
        if (field === 'stepButtonLabel' || field === 'stepButtonHref') {
          if (value === null || value === '') {
            const copy = { ...s }
            delete copy[field]
            return copy
          }
          return { ...s, [field]: value }
        }
        return { ...s, [field]: value ?? '' }
      })
      updateField('steps', next)
    }

    const addStep = () => {
      updateField('steps', [
        ...steps,
        { number: String(steps.length + 1).padStart(2, '0'), title: '', description: '' },
      ])
    }

    const removeStep = (index: number) => {
      updateField(
        'steps',
        steps.filter((_: any, i: number) => i !== index)
      )
    }

    const moveStep = (index: number, direction: 'up' | 'down') => {
      const target = direction === 'up' ? index - 1 : index + 1
      if (target < 0 || target >= steps.length) return
      const next = [...steps]
      ;[next[index], next[target]] = [next[target], next[index]]
      updateField('steps', next)
    }

    return (
      <div className="space-y-4">
        {/* En-tête de section : convention Surtitre / Titre / Description.
            Compat douce — la donnée reste stockée dans `label` (surtitre) et
            `subtitle` (description) côté legacy ; le pipeline i18n cible ces
            chemins (cf. `SECTION_I18N_POLICIES['how_it_works']`). */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.label ?? ''}
            onChange={(e) => updateField('label', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="ex. HOW IT WORKS"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Titre</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="ex. Comment ça marche"
          />
          <p className="mt-1 text-xs text-gray-500">
            Grand titre affiché au-dessus des étapes. Champ traduisible.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={data.subtitle ?? ''}
            onChange={(e) => updateField('subtitle', e.target.value)}
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="ex. Trois étapes simples pour démarrer."
          />
          <p className="mt-1 text-xs text-gray-500">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>

        {data.surface === 'dark' ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
            <p className="font-medium">Thème de surface (données legacy)</p>
            <p className="mt-1">
              La valeur <code className="rounded bg-amber-100/80 px-1">surface: &quot;dark&quot;</code> peut
              encore figurer dans le JSON, mais le rendu public force un fond clair pour ce module. Vous pouvez
              la retirer du JSON brut pour éviter toute ambiguïté.
            </p>
          </div>
        ) : null}

        <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50/80 p-4">
          <input
            id="how-it-works-hide-numbering"
            type="checkbox"
            className="mt-0.5 h-4 w-4 shrink-0 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            checked={hideStepNumbering}
            onChange={(e) => updateField('hideStepNumbering', e.target.checked)}
          />
          <label htmlFor="how-it-works-hide-numbering" className="cursor-pointer text-sm leading-snug text-gray-800">
            <span className="font-medium">Sans numérotation</span>
            <span className="mt-1 block text-xs font-normal text-gray-600">
              Les numéros d’étape (01, 02…) ne s’affichent pas sur le site. Les titres, textes, images et boutons
              par étape restent affichés.
            </span>
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CTA principal — texte</label>
            <input
              type="text"
              value={data.primaryCtaText ?? ''}
              onChange={(e) => updateField('primaryCtaText', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CTA principal — lien</label>
            <input
              type="text"
              value={data.primaryCtaHref ?? ''}
              onChange={(e) => updateField('primaryCtaHref', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="#projects"
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CTA secondaire — texte</label>
            <input
              type="text"
              value={data.secondaryCtaText ?? ''}
              onChange={(e) => updateField('secondaryCtaText', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CTA secondaire — lien</label>
            <input
              type="text"
              value={data.secondaryCtaHref ?? ''}
              onChange={(e) => updateField('secondaryCtaHref', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">Étapes</label>
            <button
              type="button"
              onClick={addStep}
              className="rounded-md bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700"
            >
              + Ajouter une étape
            </button>
          </div>

          {steps.length === 0 ? (
            <p className="rounded-md border border-gray-200 py-4 text-center text-sm text-gray-500">
              Aucune étape. Ajoutez-en une ci-dessus.
            </p>
          ) : (
            <div className="space-y-4">
              {steps.map((step: any, index: number) => (
                <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <div className="mb-3 flex items-start justify-between">
                    <span className="text-xs font-medium text-gray-500">Étape {index + 1}</span>
                    <div className="flex gap-2">
                      {index > 0 && (
                        <button
                          type="button"
                          onClick={() => moveStep(index, 'up')}
                          className="text-sm text-gray-600 hover:text-gray-900"
                          title="Monter"
                        >
                          ↑
                        </button>
                      )}
                      {index < steps.length - 1 && (
                        <button
                          type="button"
                          onClick={() => moveStep(index, 'down')}
                          className="text-sm text-gray-600 hover:text-gray-900"
                          title="Descendre"
                        >
                          ↓
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => removeStep(index)}
                        className="text-sm text-red-600 hover:text-red-900"
                      >
                        Retirer
                      </button>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {!hideStepNumbering ? (
                      <div>
                        <label className="mb-1 block text-xs font-medium text-gray-700">Numéro</label>
                        <input
                          type="text"
                          value={step.number ?? ''}
                          onChange={(e) => updateStep(index, 'number', e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                          placeholder="01"
                        />
                      </div>
                    ) : null}
                    <div>
                      <MediaField
                        value={typeof step.imageMediaId === 'string' ? step.imageMediaId : null}
                        onChange={(mediaId) => updateStep(index, 'imageMediaId', mediaId)}
                        label="Image de l’étape (optionnel)"
                        allowClear
                        preview
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        {hideStepNumbering
                          ? 'Au-dessus du titre : zone 120px de haut ; l’image entière est visible (pas de rognage), largeur adaptée au ratio.'
                          : 'Entre le numéro et le titre : zone 120px de haut ; l’image entière est visible (pas de rognage), largeur adaptée au ratio.'}
                      </p>
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-700">Titre</label>
                      <input
                        type="text"
                        value={step.title ?? ''}
                        onChange={(e) => updateStep(index, 'title', e.target.value)}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-700">Description</label>
                      <textarea
                        value={step.description ?? ''}
                        onChange={(e) => updateStep(index, 'description', e.target.value)}
                        rows={3}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <label className="mb-1 block text-xs font-medium text-gray-700">
                          Bouton d’étape — libellé (optionnel)
                        </label>
                        <input
                          type="text"
                          value={typeof step.stepButtonLabel === 'string' ? step.stepButtonLabel : ''}
                          onChange={(e) => updateStep(index, 'stepButtonLabel', e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                          placeholder="START A CONVERSATION"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs font-medium text-gray-700">
                          Bouton d’étape — lien (optionnel)
                        </label>
                        <input
                          type="text"
                          value={typeof step.stepButtonHref === 'string' ? step.stepButtonHref : ''}
                          onChange={(e) => updateStep(index, 'stepButtonHref', e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                          placeholder="https://…"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">
                      Le bouton pill noir n’apparaît sur le site que si le libellé et le lien sont tous deux
                      renseignés.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // CTA (titres, boutons, image de fond, couleur / overlay)
  if (canonical === 'cta') {
    const cmDesign = commonModuleSplit === 'design'
    const cmLocale = commonModuleSplit === 'locale'

    if (cmLocale) {
      return (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
            </label>
            <input
              type="text"
              value={data.eyebrow ?? ''}
              onChange={(e) => updateField('eyebrow', e.target.value)}
              placeholder="ex. STORY"
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
            <input
              type="text"
              value={data.title ?? ''}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="ex. Prêt à investir avec nous ?"
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">Grand titre du bloc CTA. Champ traduisible.</p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Description <span className="text-gray-500 font-normal">(Markdown)</span>
            </label>
            <textarea
              value={data.description ?? ''}
              onChange={(e) => updateField('description', e.target.value)}
              rows={4}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Paragraphes, **gras**, liens [libellé](url), listes à puces, etc.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Bouton principal — texte
            </label>
            <input
              type="text"
              value={data.primaryButtonText ?? ''}
              onChange={(e) => updateField('primaryButtonText', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Bouton secondaire — texte
            </label>
            <input
              type="text"
              value={data.secondaryButtonText ?? ''}
              onChange={(e) => updateField('secondaryButtonText', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <div>
          <MediaField
            value={data.backgroundMediaId || null}
            onChange={(mediaId) => updateField('backgroundMediaId', mediaId)}
            label="Image de fond"
            allowClear={true}
            preview={true}
          />
          <p className="mt-1 text-xs text-gray-500">
            Pleine largeur, affichée au-dessus de la couleur de fond. Réglez l’opacité de l’image pour
            un motif discret ; la teinte optionnelle s’ajoute encore au-dessus si besoin.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Couleur de fond (hex)
            </label>
            <div className="flex gap-2">
              <input
                type="color"
                value={
                  /^#[0-9A-Fa-f]{6}$/.test(data.backgroundColor || '')
                    ? data.backgroundColor
                    : '#000000'
                }
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-gray-300"
                title="Choisir une couleur"
              />
              <input
                type="text"
                value={data.backgroundColor ?? '#000000'}
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                placeholder="#000000"
                className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Opacité de l’image sur la couleur (0–1)
            </label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={
                typeof data.backgroundImageOpacity === 'number'
                  ? data.backgroundImageOpacity
                  : 1
              }
              onChange={(e) =>
                updateField('backgroundImageOpacity', parseFloat(e.target.value) || 0)
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              1 = image pleine ; vers 0 le motif s’efface et la couleur de fond domine.
            </p>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Teinte par-dessus (0–1), 0 = désactivée
          </label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={
              typeof data.overlayOpacity === 'number' ? data.overlayOpacity : 0.55
            }
            onChange={(e) =>
              updateField('overlayOpacity', parseFloat(e.target.value) || 0)
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Couche de couleur (même teinte que le fond) au-dessus de l’image pour assombrir ou unifier.
          </p>
        </div>

        {!cmDesign && (
          <>
            {/* En-tête de section : convention Surtitre / Titre / Description.
                Tous les 3 champs sont optionnels et traduisibles
                (cf. `SECTION_I18N_POLICIES['cta']`). */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
              </label>
              <input
                type="text"
                value={data.eyebrow ?? ''}
                onChange={(e) => updateField('eyebrow', e.target.value)}
                placeholder="ex. STORY"
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
              </p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
              <input
                type="text"
                value={data.title ?? ''}
                onChange={(e) => updateField('title', e.target.value)}
                placeholder="ex. Prêt à investir avec nous ?"
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Grand titre du bloc CTA. Champ traduisible.
              </p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description <span className="text-gray-500 font-normal">(Markdown)</span>
              </label>
              <textarea
                value={data.description ?? ''}
                onChange={(e) => updateField('description', e.target.value)}
                rows={4}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Paragraphes, **gras**, liens [libellé](url), listes à puces, etc.
              </p>
            </div>
          </>
        )}

        {cmDesign ? (
          <p className="rounded-md border border-amber-100 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
            Surtitre, titre, description et libellés des boutons se règlent dans l’onglet de langue
            ci-dessous.
          </p>
        ) : null}

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Alignement du texte
          </label>
          <select
            value={data.contentTextAlign === 'justify' ? 'justify' : 'center'}
            onChange={(e) =>
              updateField('contentTextAlign', e.target.value as 'center' | 'justify')
            }
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value="center">Centré</option>
            <option value="justify">Justifié (bord à bord)</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            S’applique à la description. Le titre et le surtitre restent centrés.
          </p>
        </div>

        <div className="flex flex-wrap gap-6">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={data.showPrimaryButton !== false}
              onChange={(e) => updateField('showPrimaryButton', e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            Afficher le bouton principal
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={data.showSecondaryButton !== false}
              onChange={(e) => updateField('showSecondaryButton', e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            Afficher le bouton secondaire
          </label>
        </div>

        {!cmDesign ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Bouton principal — texte
                </label>
                <input
                  type="text"
                  value={data.primaryButtonText ?? ''}
                  onChange={(e) => updateField('primaryButtonText', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Bouton principal — lien
                </label>
                <input
                  type="text"
                  value={data.primaryButtonHref ?? ''}
                  onChange={(e) => updateField('primaryButtonHref', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Bouton secondaire — texte
                </label>
                <input
                  type="text"
                  value={data.secondaryButtonText ?? ''}
                  onChange={(e) => updateField('secondaryButtonText', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Bouton secondaire — lien
                </label>
                <input
                  type="text"
                  value={data.secondaryButtonHref ?? ''}
                  onChange={(e) => updateField('secondaryButtonHref', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Bouton principal — lien
              </label>
              <input
                type="text"
                value={data.primaryButtonHref ?? ''}
                onChange={(e) => updateField('primaryButtonHref', e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Bouton secondaire — lien
              </label>
              <input
                type="text"
                value={data.secondaryButtonHref ?? ''}
                onChange={(e) => updateField('secondaryButtonHref', e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </>
        )}
      </div>
    )
  }

  // Figma — Hero texte (sans média)
  if (canonical === 'figma_simple_hero') {
    const bg = /^#[0-9A-Fa-f]{6}$/.test(data.backgroundColor || '') ? data.backgroundColor : '#ffffff'
    const fg = /^#[0-9A-Fa-f]{6}$/.test(data.textColor || '') ? data.textColor : '#000000'
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Bloc titre + paragraphe (design Figma « About »). Couleurs en hex ; pas d’image de fond.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <textarea
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={4}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Fond (hex)</label>
            <div className="flex gap-2">
              <input
                type="color"
                value={bg}
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-gray-300"
              />
              <input
                type="text"
                value={data.backgroundColor ?? '#ffffff'}
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Texte (hex)</label>
            <div className="flex gap-2">
              <input
                type="color"
                value={fg}
                onChange={(e) => updateField('textColor', e.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-gray-300"
              />
              <input
                type="text"
                value={data.textColor ?? '#000000'}
                onChange={(e) => updateField('textColor', e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
              />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Figma — Grille de stats (max 6 sauf 4 colonnes → max 8)
  if (canonical === 'figma_stats_grid') {
    const stats: { value?: string; label?: string }[] = Array.isArray(data.stats) ? data.stats : []
    const columns =
      data.columns === 6 ? 6 : data.columns === 4 ? 4 : 3
    const maxStats = columns === 4 ? 8 : 6

    const setStats = (next: typeof stats) => onChange({ ...data, stats: next })

    const updateStat = (index: number, field: 'value' | 'label', value: string) => {
      const next = [...stats]
      if (!next[index]) next[index] = {}
      next[index] = { ...next[index], [field]: value }
      setStats(next)
    }

    const addStat = () => {
      if (stats.length >= maxStats) return
      setStats([...stats, { value: '', label: '' }])
    }

    const removeStat = (index: number) => {
      setStats(stats.filter((_, i) => i !== index))
    }

    return (
      <div className="space-y-4">
        {/* En-tête de section : convention Surtitre / Titre / Description
            (cf. `media_text`, `figma_testimonial_cards`, `key_figures`…).
            Tous les 3 champs sont optionnels et traduisibles
            (cf. `SECTION_I18N_POLICIES['figma_stats_grid']`). */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. CHIFFRES CLÉS"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Notre impact en un coup d'œil"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Grand titre affiché au-dessus de la grille. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="ex. Quelques indicateurs représentatifs de l'activité."
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Colonnes</label>
          <select
            value={columns}
            onChange={(e) => {
              const v = Number(e.target.value)
              const n = v === 6 ? 6 : v === 4 ? 4 : 3
              if (n !== 4 && Array.isArray(data.stats) && data.stats.length > 6) {
                onChange({ ...data, columns: n, stats: data.stats.slice(0, 6) })
              } else {
                onChange({ ...data, columns: n })
              }
            }}
            className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2"
          >
            <option value={3}>3 (2 lignes max si 6 stats)</option>
            <option value={4}>4 (2 lignes max si 8 stats)</option>
            <option value={6}>6 (une ligne)</option>
          </select>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Indicateurs ({stats.length}/{maxStats})
          </span>
          <button
            type="button"
            onClick={addStat}
            disabled={stats.length >= maxStats}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            Ajouter
          </button>
        </div>
        <div className="space-y-3">
          {stats.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun indicateur. Cliquez sur « Ajouter ».</p>
          ) : (
            stats.map((row, index) => (
              <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="mb-2 flex justify-between">
                  <span className="text-xs text-gray-500">#{index + 1}</span>
                  <button
                    type="button"
                    onClick={() => removeStat(index)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Retirer
                  </button>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Valeur</label>
                    <input
                      type="text"
                      value={row.value ?? ''}
                      onChange={(e) => updateStat(index, 'value', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Libellé</label>
                    <input
                      type="text"
                      value={row.label ?? ''}
                      onChange={(e) => updateStat(index, 'label', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    )
  }

  // Chiffres clés — grille sombre 3×2, fond image optionnel
  if (canonical === 'key_figures') {
    const stats: { value?: string; label?: string }[] = Array.isArray(data.stats) ? data.stats : []
    const setStats = (next: typeof stats) => onChange({ ...data, stats: next })
    const updateStat = (index: number, field: 'value' | 'label', value: string) => {
      const next = [...stats]
      if (!next[index]) next[index] = {}
      next[index] = { ...next[index], [field]: value }
      setStats(next)
    }
    const addStat = () => {
      if (stats.length >= 6) return
      setStats([...stats, { value: '', label: '' }])
    }
    const removeStat = (index: number) => {
      setStats(stats.filter((_, i) => i !== index))
    }

    return (
      <div className="space-y-4">
        <div>
          <MediaField
            value={data.backgroundMediaId || null}
            onChange={(mediaId) => updateField('backgroundMediaId', mediaId)}
            label="Image de fond (pleine largeur)"
            allowClear={true}
            preview={true}
          />
          <p className="mt-1 text-xs text-gray-500">
            Affichée au-dessus de la couleur ; baissez l’opacité pour un motif léger.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Couleur de fond (hex)
            </label>
            <div className="flex gap-2">
              <input
                type="color"
                value={
                  /^#[0-9A-Fa-f]{6}$/.test(data.backgroundColor || '')
                    ? data.backgroundColor
                    : '#000000'
                }
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-gray-300"
              />
              <input
                type="text"
                value={data.backgroundColor ?? '#000000'}
                onChange={(e) => updateField('backgroundColor', e.target.value)}
                placeholder="#000000"
                className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Opacité de l’image (0–1)
            </label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={
                typeof data.backgroundImageOpacity === 'number'
                  ? data.backgroundImageOpacity
                  : 1
              }
              onChange={(e) =>
                updateField('backgroundImageOpacity', parseFloat(e.target.value) || 0)
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Teinte par-dessus (0–1), 0 = aucune
          </label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={typeof data.overlayOpacity === 'number' ? data.overlayOpacity : 0}
            onChange={(e) =>
              updateField('overlayOpacity', parseFloat(e.target.value) || 0)
            }
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Surtitre</label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. STORY"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Titre de section (optionnel)
          </label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Indicateurs ({stats.length}/6) — grille 3×2
          </span>
          <button
            type="button"
            onClick={addStat}
            disabled={stats.length >= 6}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            Ajouter
          </button>
        </div>
        <div className="space-y-3">
          {stats.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun indicateur. Cliquez sur « Ajouter ».</p>
          ) : (
            stats.map((row, index) => (
              <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="mb-2 flex justify-between">
                  <span className="text-xs text-gray-500">#{index + 1}</span>
                  <button
                    type="button"
                    onClick={() => removeStat(index)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Retirer
                  </button>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Valeur</label>
                    <input
                      type="text"
                      value={row.value ?? ''}
                      onChange={(e) => updateStat(index, 'value', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Libellé</label>
                    <input
                      type="text"
                      value={row.label ?? ''}
                      onChange={(e) => updateStat(index, 'label', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    )
  }

  // Figma — Cartes témoignages
  if (canonical === 'figma_testimonial_cards') {
    const items: {
      author?: string
      role?: string
      content?: string
      avatar?: string
      avatarMediaId?: string
      backgroundColor?: string
    }[] = Array.isArray(data.items) ? data.items : []

    const setItems = (next: typeof items) => onChange({ ...data, items: next })

    const updateItem = (
      index: number,
      field: 'author' | 'role' | 'content' | 'backgroundColor',
      value: string,
    ) => {
      const next = [...items]
      if (!next[index]) next[index] = {}
      next[index] = { ...next[index], [field]: value }
      setItems(next)
    }

    const setAvatarMedia = (index: number, mediaId: string | null) => {
      const next = [...items]
      if (!next[index]) next[index] = {}
      const row = { ...next[index] }
      if (mediaId) {
        row.avatarMediaId = mediaId
        delete row.avatar
      } else {
        delete row.avatarMediaId
      }
      next[index] = row
      setItems(next)
    }

    const addItem = () =>
      setItems([...items, { author: '', role: '', content: '', backgroundColor: '#f4f4f4' }])

    const removeItem = (index: number) => setItems(items.filter((_, i) => i !== index))

    return (
      <div className="space-y-4">
        {/* En-tête de section : aligné sur la convention majoritaire du repo
            (cf. `cta`, `key_figures`, `company_map`, `media_text`…). On évite
            le fieldset bleu spécifique : labels « Surtitre / Titre / Description »
            + microcopy sous chaque champ. Tous les 3 champs sont traduisibles
            via `SECTION_I18N_POLICIES['figma_testimonial_cards']`. */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. TÉMOIGNAGES"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Ils nous font confiance"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Grand titre affiché au-dessus des cartes. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="ex. Avis et retours d'expérience de nos clients."
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Disposition des cartes</label>
          <select
            value={data.cardsPerRow === 2 ? 2 : 1}
            onChange={(e) =>
              updateField('cardsPerRow', e.target.value === '2' ? 2 : 1)
            }
            className="w-full max-w-md rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value={1}>1 par ligne</option>
            <option value={2}>2 par ligne</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            En « 2 par ligne », les cartes sont côte à côte sur écran large ; une colonne sur mobile.
          </p>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Cartes</span>
          <button
            type="button"
            onClick={addItem}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white"
          >
            Ajouter une carte
          </button>
        </div>
        {items.length === 0 ? (
          <p className="text-sm text-gray-500">Aucune carte. Utilisez « Ajouter une carte ».</p>
        ) : (
          <div className="space-y-4">
            {items.map((item, index) => (
              <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="mb-3 flex justify-between">
                  <span className="text-xs font-medium text-gray-500">Carte {index + 1}</span>
                  <button
                    type="button"
                    onClick={() => removeItem(index)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Retirer
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Auteur</label>
                    <input
                      type="text"
                      value={item.author ?? ''}
                      onChange={(e) => updateItem(index, 'author', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Rôle</label>
                    <input
                      type="text"
                      value={item.role ?? ''}
                      onChange={(e) => updateItem(index, 'role', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div className="mt-3">
                  <label className="mb-1 block text-xs font-medium text-gray-700">Texte</label>
                  <textarea
                    value={item.content ?? ''}
                    onChange={(e) => updateItem(index, 'content', e.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div className="mt-3">
                  <MediaField
                    value={item.avatarMediaId ?? null}
                    onChange={(mediaId) => setAvatarMedia(index, mediaId)}
                    label="Photo (avatar)"
                    allowClear={true}
                    preview={true}
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Choisir une image dans Média. Une ancienne URL saisie dans le JSON brut reste utilisée
                    si aucun média n’est sélectionné.
                  </p>
                </div>
                <div className="mt-3">
                  <label className="mb-1 block text-xs font-medium text-gray-700">Fond carte (hex)</label>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={
                        /^#[0-9A-Fa-f]{6}$/.test(item.backgroundColor || '')
                          ? item.backgroundColor
                          : '#f4f4f4'
                        }
                        onChange={(e) => updateItem(index, 'backgroundColor', e.target.value)}
                        className="h-9 w-12 cursor-pointer rounded border border-gray-300"
                      />
                      <input
                        type="text"
                        value={item.backgroundColor ?? '#f4f4f4'}
                      onChange={(e) => updateItem(index, 'backgroundColor', e.target.value)}
                      className="min-w-0 flex-1 rounded-md border border-gray-300 px-2 py-1.5 font-mono text-sm"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Media & texte (DS) — image médiathèque, option image à droite (`media_text`, `media_text_2`, …)
  if (canonical === 'media_text') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Bloc deux colonnes sur fond blanc (pleine largeur) : titre, description et image (médiathèque). Plusieurs
          blocs : clés <code className="rounded bg-gray-100 px-1">media_text</code>,{' '}
          <code className="rounded bg-gray-100 px-1">media_text_2</code>, etc. (idem pour les autres types du
          catalogue : <code className="rounded bg-gray-100 px-1">cta_2</code>, …)
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. Notre approche"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau (recommandé si la
            traduction n&rsquo;est pas encore prête). Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <textarea
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={5}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <MediaField
            value={data.imageMediaId || null}
            onChange={(mediaId) => updateField('imageMediaId', mediaId)}
            label="Image"
            allowClear={true}
            preview={true}
          />
        </div>
        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            checked={data.mediaRight === true}
            onChange={(e) => updateField('mediaRight', e.target.checked)}
          />
          <span>
            <span className="block text-sm font-medium text-gray-900">Image à droite (MediaRight)</span>
            <span className="mt-1 block text-xs text-gray-600">
              Activé : texte à gauche, image à droite. Désactivé : image à gauche, texte à droite (défaut).
            </span>
          </span>
        </label>
      </div>
    )
  }

  // Testimonials — surtitre, titre, description, cartes
  if (canonical === 'testimonials') {
    type TestimonialRow = {
      name?: string
      text?: string
      rating?: number
      title?: string
      avatarMediaId?: string
    }
    const items: TestimonialRow[] = Array.isArray(data.items) ? data.items : []

    const setItems = (next: TestimonialRow[]) => onChange({ ...data, items: next })

    const updateItem = (
      index: number,
      field: keyof TestimonialRow,
      value: string | number,
    ) => {
      const next = [...items]
      if (!next[index]) next[index] = {}
      next[index] = { ...next[index], [field]: value }
      setItems(next)
    }

    const setAvatarMedia = (index: number, mediaId: string | null) => {
      const next = [...items]
      if (!next[index]) next[index] = {}
      const row = { ...next[index] }
      if (mediaId) {
        row.avatarMediaId = mediaId
      } else {
        delete row.avatarMediaId
      }
      next[index] = row
      setItems(next)
    }

    const addItem = () =>
      setItems([...items, { name: '', text: '', rating: 5, title: '' }])

    const removeItem = (index: number) => setItems(items.filter((_, i) => i !== index))

    return (
      <div className="space-y-4">
        {/* En-tête de section : convention Surtitre / Titre / Description.
            Tous les 3 champs sont optionnels et traduisibles
            (cf. `SECTION_I18N_POLICIES['testimonials']`). */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Surtitre <span className="text-gray-500 font-normal">(pastille au-dessus du titre)</span>
          </label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. TÉMOIGNAGES"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Laisser vide pour ne PAS afficher de bandeau. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <textarea
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            rows={2}
            placeholder="ex. Ils nous font confiance"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Grand titre affiché au-dessus des cartes. Champ traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            placeholder="ex. Avis et retours d'expérience de nos clients."
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Court paragraphe sous le titre (chapô). Champ traduisible.
          </p>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Témoignages ({items.length})</span>
          <button
            type="button"
            onClick={addItem}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white"
          >
            Ajouter une carte
          </button>
        </div>
        <div className="space-y-3">
          {items.length === 0 ? (
            <p className="text-sm text-gray-500">Aucune carte. Cliquez sur « Ajouter une carte ».</p>
          ) : (
            items.map((row, index) => (
              <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="mb-2 flex justify-between">
                  <span className="text-xs text-gray-500">Carte #{index + 1}</span>
                  <button
                    type="button"
                    onClick={() => removeItem(index)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Retirer
                  </button>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Nom</label>
                    <input
                      type="text"
                      value={row.name ?? ''}
                      onChange={(e) => updateItem(index, 'name', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Rôle (optionnel)</label>
                    <input
                      type="text"
                      value={row.title ?? ''}
                      onChange={(e) => updateItem(index, 'title', e.target.value)}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="mb-1 block text-xs font-medium text-gray-700">Texte</label>
                    <textarea
                      value={row.text ?? ''}
                      onChange={(e) => updateItem(index, 'text', e.target.value)}
                      rows={3}
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">Note (0–5)</label>
                    <input
                      type="number"
                      min={0}
                      max={5}
                      value={row.rating ?? 5}
                      onChange={(e) =>
                        updateItem(index, 'rating', parseInt(e.target.value, 10) || 0)
                      }
                      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <MediaField
                      value={row.avatarMediaId ?? null}
                      onChange={(mediaId) => setAvatarMedia(index, mediaId)}
                      label="Photo (avatar)"
                      allowClear={true}
                      preview={true}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Image carrée ou portrait dans Média. Sans choix, un avatar de démonstration s’affiche.
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    )
  }

  // Company map — carte en fond, corps Markdown sous la carte
  if (canonical === 'company_map') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          La carte (image médiathèque) est placée derrière le texte et déborde légèrement sur la zone titre et la zone
          corps. Utilisez une image large (PNG/SVG) avec transparence ou fond blanc.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Surtitre</label>
          <input
            type="text"
            value={data.eyebrow ?? ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. PRÉSENCE INTERNATIONALE"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
          <textarea
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description (chapô sous le titre)</label>
          <textarea
            value={data.description ?? ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <MediaField
            value={data.backgroundMediaId || null}
            onChange={(mediaId) => updateField('backgroundMediaId', mediaId)}
            label="Image de fond (carte)"
            allowClear={true}
            preview={true}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Contenu corps (Markdown, sous la carte)
          </label>
          <textarea
            value={data.bodyContent ?? ''}
            onChange={(e) => updateField('bodyContent', e.target.value)}
            rows={12}
            placeholder="Paragraphes, **gras**, listes, liens…"
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
      </div>
    )
  }

  /** Hero article 100 % CMS (bandeau type page article, sans lecteur Prisma) */
  if (canonical === 'blog_article_hero') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Titre, chapô, méta et visuel sont saisis ici pour la langue d’édition active. Aucun contenu ne
          provient d’un article publié — pour le corps et les blocs, utilisez d’autres modules ou le{' '}
          <strong>Blog — article complet (lecture)</strong> sur le gabarit article.
        </p>
        <div className="flex items-center gap-2">
          <input
            id="blog-article-hero-show-breadcrumb"
            type="checkbox"
            checked={data.showBreadcrumb === true}
            onChange={(e) => updateField('showBreadcrumb', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-article-hero-show-breadcrumb" className="text-sm text-gray-700">
            Afficher le fil d’Ariane (Blog › segment courant)
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Libellé du lien vers le blog
          </label>
          <input
            type="text"
            value={data.blogLabel ?? ''}
            onChange={(e) => updateField('blogLabel', e.target.value)}
            placeholder="Laissez vide pour le libellé par défaut du site"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Dernier segment du fil (si vide = titre ci-dessous)
          </label>
          <input
            type="text"
            value={data.breadcrumbCurrentText ?? ''}
            onChange={(e) => updateField('breadcrumbCurrentText', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre (h1)</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Chapô</label>
          <textarea
            value={data.standfirst ?? ''}
            onChange={(e) => updateField('standfirst', e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Pastilles catégories (une par ligne)
          </label>
          <textarea
            value={Array.isArray(data.categoryPillLabels) ? data.categoryPillLabels.join('\n') : ''}
            onChange={(e) => {
              const lines = e.target.value
                .split('\n')
                .map((s) => s.trim())
                .filter((s) => s.length > 0)
              updateField('categoryPillLabels', lines)
            }}
            rows={3}
            placeholder={'Analyse\nMarchés'}
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-sans text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Si vide : une pastille « segment » peut s’afficher avec le champ ci-dessous.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Pastille segment (si aucune catégorie)
          </label>
          <input
            type="text"
            value={data.editorialPillLabel ?? ''}
            onChange={(e) => updateField('editorialPillLabel', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Auteur (nom)</label>
            <input
              type="text"
              value={data.authorName ?? ''}
              onChange={(e) => updateField('authorName', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Rôle / fonction</label>
            <input
              type="text"
              value={data.authorRole ?? ''}
              onChange={(e) => updateField('authorRole', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            id="blog-article-hero-author-prefix"
            type="checkbox"
            checked={data.showAuthorByPrefix === true}
            onChange={(e) => updateField('showAuthorByPrefix', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-article-hero-author-prefix" className="text-sm text-gray-700">
            Préfixe « Par » (ou équivalent) devant l’auteur
          </label>
        </div>
        <div className="flex items-center gap-2">
          <input
            id="blog-article-hero-show-reading"
            type="checkbox"
            checked={data.showReadingTime !== false}
            onChange={(e) => updateField('showReadingTime', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-article-hero-show-reading" className="text-sm text-gray-700">
            Afficher la ligne durée de lecture
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Texte durée de lecture (libre, ex. « 4 min de lecture »)
          </label>
          <input
            type="text"
            value={data.readingTimeText ?? ''}
            onChange={(e) => updateField('readingTimeText', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              id="blog-article-hero-show-date"
              type="checkbox"
              checked={data.showDate !== false}
              onChange={(e) => updateField('showDate', e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="blog-article-hero-show-date" className="text-sm text-gray-700">
              Afficher la date de parution
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="blog-article-hero-show-updated"
              type="checkbox"
              checked={data.showUpdatedDate === true}
              onChange={(e) => updateField('showUpdatedDate', e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="blog-article-hero-show-updated" className="text-sm text-gray-700">
              Afficher la date de mise à jour
            </label>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Date de parution (ISO, ex. 2024-06-15)
            </label>
            <input
              type="text"
              value={data.publishedAtIso ?? ''}
              onChange={(e) => updateField('publishedAtIso', e.target.value)}
              placeholder="2024-06-15 ou date/heure ISO complète"
              className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Date de mise à jour (ISO)</label>
            <input
              type="text"
              value={data.updatedAtIso ?? ''}
              onChange={(e) => updateField('updatedAtIso', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Légende au-dessus du visuel (optionnel)
          </label>
          <input
            type="text"
            value={data.coverTitle ?? ''}
            onChange={(e) => updateField('coverTitle', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <MediaField
            value={data.imageMediaId || null}
            onChange={(mediaId) => updateField('imageMediaId', mediaId)}
            label="Image de couverture (médiathèque)"
            allowClear={true}
            preview={true}
          />
          <p className="mt-1 text-xs text-gray-500">
            Si une URL vidéo est renseignée ci-dessous, la vidéo prime sur l’image.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">URL vidéo embarquée (YouTube / Vimeo)</label>
          <input
            type="text"
            value={data.videoUrl ?? ''}
            onChange={(e) => updateField('videoUrl', e.target.value)}
            placeholder="https://…"
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Crédit photo</label>
            <input
              type="text"
              value={data.coverCredit ?? ''}
              onChange={(e) => updateField('coverCredit', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Source</label>
            <input
              type="text"
              value={data.coverSource ?? ''}
              onChange={(e) => updateField('coverSource', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>
    )
  }

  /** Lecteur article blog — gabarit page détail (libellés enveloppe, traduisibles) */
  if (canonical === 'blog_article_reader') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Le contenu de l’article (titres, blocs, médias) est géré dans{' '}
          <strong>Articles</strong> · ici seulement les textes d’enveloppe (fil d’Ariane, sommaire, durée de
          lecture, etc.) pour la langue d’édition active.
        </p>
        <div className="flex items-center gap-2">
          <input
            id="blog-reader-show-breadcrumb"
            type="checkbox"
            checked={data.showBreadcrumb !== false}
            onChange={(e) => updateField('showBreadcrumb', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-reader-show-breadcrumb" className="text-sm text-gray-700">
            Afficher le fil d’Ariane (Blog › titre de l’article)
          </label>
        </div>
        <p className="text-xs text-gray-500">
          Sur le gabarit article, laissez en général activé. Pour un bandeau 100 % CMS ailleurs, préférez le
          module <strong>Blog — en-tête type article (CMS)</strong>.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Libellé du fil (lien vers le blog)
          </label>
          <input
            type="text"
            value={data.blogLabel ?? ''}
            onChange={(e) => updateField('blogLabel', e.target.value)}
            placeholder="Laissez vide pour le libellé par défaut du site"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Titre du sommaire (colonne « dans cet article »)
          </label>
          <input
            type="text"
            value={data.tocTitle ?? ''}
            onChange={(e) => updateField('tocTitle', e.target.value)}
            placeholder="ex. Dans cet article — vide = libellé par défaut"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="blog-reader-show-toc"
            type="checkbox"
            checked={data.showToc !== false}
            onChange={(e) => updateField('showToc', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-reader-show-toc" className="text-sm text-gray-700">
            Afficher le sommaire (si assez de titres)
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Nombre minimum de titres pour afficher le sommaire
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={typeof data.tocMinHeadings === 'number' ? data.tocMinHeadings : 3}
            onChange={(e) => updateField('tocMinHeadings', parseInt(e.target.value, 10) || 3)}
            className="w-32 rounded-md border border-gray-300 px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre du bloc pièces jointes</label>
          <input
            type="text"
            value={data.documentsTitle ?? ''}
            onChange={(e) => updateField('documentsTitle', e.target.value)}
            placeholder="Vide = libellé par défaut"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Texte durée de lecture (modèle)</label>
          <input
            type="text"
            value={data.readingTimeLabel ?? ''}
            onChange={(e) => updateField('readingTimeLabel', e.target.value)}
            placeholder="ex. {{minutes}} min de lecture"
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Placeholders : <code className="rounded bg-gray-100 px-1">{'{{minutes}}'}</code> ou{' '}
            <code className="rounded bg-gray-100 px-1">{'{{count}}'}</code> — vide = texte système (min. de
            lecture i18n).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            id="blog-reader-author-prefix"
            type="checkbox"
            checked={data.showAuthorByPrefix === true}
            onChange={(e) => updateField('showAuthorByPrefix', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-reader-author-prefix" className="text-sm text-gray-700">
            Préfixe « Par » (ou équivalent) devant l’auteur
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Texte du préfixe auteur
          </label>
          <input
            type="text"
            value={data.authorPrefixLabel ?? ''}
            onChange={(e) => updateField('authorPrefixLabel', e.target.value)}
            placeholder="ex. Par / By"
            disabled={data.showAuthorByPrefix !== true}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:text-gray-400"
          />
          <p className="mt-1 text-xs text-gray-500">
            Vide = libellé site par défaut (i18n « Par » / « By »). Saisir une valeur par locale via la barre
            de langue admin.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            id="blog-reader-show-docs"
            type="checkbox"
            checked={data.showDocuments !== false}
            onChange={(e) => updateField('showDocuments', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-reader-show-docs" className="text-sm text-gray-700">
            Afficher la zone documents sous l’article
          </label>
        </div>
        {/*
          Date de mise à jour : option **masquée** depuis avril 2026 — produit a
          décidé de n'afficher que la date de création. Le code Zod / mapping /
          rendu reste en place (réversible). Pour réactiver, dé-commenter le
          bloc ci-dessous et remettre `showUpdatedDate: true` dans
          `defaultData` (`library.ts`).

        <div className="flex items-center gap-2">
          <input
            id="blog-reader-show-updated"
            type="checkbox"
            checked={data.showUpdatedDate === true}
            onChange={(e) => updateField('showUpdatedDate', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-reader-show-updated" className="text-sm text-gray-700">
            Afficher la date de mise à jour (en plus de la parution)
          </label>
        </div>
        */}
      </div>
    )
  }

  /** Blog — article à la une (données article = base ; ce module règle surtitre et blocs visibles) */
  if (canonical === 'blog_hero') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Bandeau tête de page blog : surtitre éditorial et affichage des zones (chapô, méta). Le titre et le
          texte de l’article viennent du contenu publié, pas de ces champs.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Surtitre <span className="text-gray-500 font-normal">(pastille)</span>
          </label>
          <input
            type="text"
            value={typeof data.eyebrow === 'string' ? data.eyebrow : ''}
            onChange={(e) => updateField('eyebrow', e.target.value)}
            placeholder="ex. À la une"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Traduisible.</p>
        </div>
        <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50/80 p-4">
          <p className="text-sm font-medium text-gray-800">Blocs visibles</p>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              checked={data.showEyebrow !== false}
              onChange={(e) => updateField('showEyebrow', e.target.checked)}
            />
            <span className="text-sm text-gray-700">Afficher le surtitre</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              checked={data.showStandfirst !== false}
              onChange={(e) => updateField('showStandfirst', e.target.checked)}
            />
            <span className="text-sm text-gray-700">Afficher le chapô (standfirst)</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              checked={data.showMeta !== false}
              onChange={(e) => updateField('showMeta', e.target.checked)}
            />
            <span className="text-sm text-gray-700">Afficher les métadonnées (date, etc.)</span>
          </label>
        </div>
      </div>
    )
  }

  /** Blog — flux paginé « charger plus » */
  if (canonical === 'blog_feed') {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Liste des articles avec pagination par bouton. Les textes vides pour l’état vide ou le bouton
          peuvent laisser le site appliquer des libellés par défaut selon la langue.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre de section</label>
          <input
            type="text"
            value={typeof data.title === 'string' ? data.title : ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Derniers articles"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Traduisible.</p>
        </div>
        <label className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            checked={data.showTitle !== false}
            onChange={(e) => updateField('showTitle', e.target.checked)}
          />
          <span className="text-sm text-gray-700">Afficher le titre</span>
        </label>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Taille de page (articles par chargement)
          </label>
          <input
            type="number"
            min={1}
            max={50}
            value={
              typeof data.pageSize === 'number' && Number.isFinite(data.pageSize) ? data.pageSize : 10
            }
            onChange={(e) => {
              const v = parseInt(e.target.value, 10)
              updateField('pageSize', Number.isFinite(v) ? Math.min(50, Math.max(1, v)) : 10)
            }}
            className="w-32 rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Non traduisible.</p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Libellé du bouton « charger plus »
          </label>
          <input
            type="text"
            value={typeof data.loadMoreLabel === 'string' ? data.loadMoreLabel : ''}
            onChange={(e) => updateField('loadMoreLabel', e.target.value)}
            placeholder="Laisser vide pour le libellé par défaut du site"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Traduisible.</p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre — liste vide</label>
          <input
            type="text"
            value={typeof data.emptyStateTitle === 'string' ? data.emptyStateTitle : ''}
            onChange={(e) => updateField('emptyStateTitle', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Texte — liste vide</label>
          <textarea
            value={typeof data.emptyStateBody === 'string' ? data.emptyStateBody : ''}
            onChange={(e) => updateField('emptyStateBody', e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
      </div>
    )
  }

  /** Mosaïque d’articles — liste blog */
  if (canonical === 'blog_mosaic') {
    return (
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre de la section</label>
          <input
            type="text"
            value={typeof data.title === 'string' ? data.title : ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. À ne pas manquer"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Traduisible (FR / EN / IT).</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="blog-mosaic-show-title"
            checked={data.showTitle !== false}
            onChange={(e) => updateField('showTitle', e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="blog-mosaic-show-title" className="text-sm text-gray-700">
            Afficher le titre
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Articles par page (limite CMS)
          </label>
          <input
            type="number"
            min={0}
            max={99}
            value={typeof data.limit === 'number' && Number.isFinite(data.limit) ? data.limit : 3}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10)
              updateField('limit', Number.isFinite(v) ? v : 3)
            }}
            className="w-32 rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            À l’affichage : arrondi au multiple de 3 supérieur (0 → 3). Non traduisible.
          </p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Libellé CTA « tout voir » (optionnel)
          </label>
          <input
            type="text"
            value={typeof data.ctaLabel === 'string' ? data.ctaLabel : ''}
            onChange={(e) => updateField('ctaLabel', e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Traduisible — non affiché sur le site actuellement ; conservé pour cohérence CMS.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Pagination — bouton précédent
            </label>
            <input
              type="text"
              value={
                typeof data.paginationPrevLabel === 'string' ? data.paginationPrevLabel : ''
              }
              onChange={(e) => updateField('paginationPrevLabel', e.target.value)}
              placeholder="Précédent"
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">Traduisible. Vide = libellé par défaut du site.</p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Pagination — bouton suivant
            </label>
            <input
              type="text"
              value={
                typeof data.paginationNextLabel === 'string' ? data.paginationNextLabel : ''
              }
              onChange={(e) => updateField('paginationNextLabel', e.target.value)}
              placeholder="Suivant"
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            />
            <p className="mt-1 text-xs text-gray-500">Traduisible. Vide = libellé par défaut du site.</p>
          </div>
        </div>
      </div>
    )
  }

  /** Corps Vault — gabarit offre exclusive (slot sans champs CMS) */
  if (canonical === 'exclusive_offer_vault') {
    return (
      <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm text-gray-700">
          Ce bloc affiche le contenu <strong>Vault Builder</strong> de l’offre affichée sur le site. Rien à
          configurer ici — éditer chaque offre dans <strong>Exclusive Offers</strong> ou{' '}
          <strong>Vault Builder</strong>.
        </p>
      </div>
    )
  }

  /** Partage réseaux (shareSM) — gabarit article */
  if (canonical === 'share_sm') {
    const items = Array.isArray(data.items) ? data.items : []
    const generateId = () => `sm-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    const addItem = () => {
      updateField('items', [
        ...items,
        { id: generateId(), platform: 'link', label: '', href: '' },
      ])
    }
    const removeAt = (index: number) => {
      updateField(
        'items',
        items.filter((_: unknown, i: number) => i !== index),
      )
    }
    const patchAt = (index: number, patch: Record<string, unknown>) => {
      updateField(
        'items',
        items.map((item: Record<string, unknown>, i: number) =>
          i === index ? { ...item, ...patch } : item,
        ),
      )
    }
    const moveItem = (index: number, direction: 'up' | 'down') => {
      const next = [...items]
      const target = direction === 'up' ? index - 1 : index + 1
      if (target >= 0 && target < next.length) {
        ;[next[index], next[target]] = [next[target], next[index]]
        updateField('items', next)
      }
    }
    const platforms: { v: string; l: string }[] = [
      { v: 'facebook', l: 'Facebook' },
      { v: 'x', l: 'X (Twitter)' },
      { v: 'linkedin', l: 'LinkedIn' },
      { v: 'instagram', l: 'Instagram' },
      { v: 'youtube', l: 'YouTube' },
      { v: 'link', l: 'Lien générique' },
    ]
    return (
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Titre du module</label>
          <input
            type="text"
            value={data.title ?? ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="ex. Partager"
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-500">Traduisible (FR / EN / IT).</p>
        </div>
        <p className="text-xs text-gray-600">
          Dans l’URL :{' '}
          <code className="rounded bg-gray-100 px-1">{'{{encodedUrl}}'}</code>,{' '}
          <code className="rounded bg-gray-100 px-1">{'{{encodedTitle}}'}</code>,{' '}
          <code className="rounded bg-gray-100 px-1">{'{{encodedShareText}}'}</code> (titre + saut de ligne + URL, encodés), ou{' '}
          <code className="rounded bg-gray-100 px-1">{'{{url}}'}</code> /{' '}
          <code className="rounded bg-gray-100 px-1">{'{{title}}'}</code> non encodés.
        </p>
        <div className="space-y-3">
          {items.map((item: Record<string, unknown>, index: number) => (
            <div
              key={typeof item.id === 'string' ? item.id : `row-${index}`}
              className="space-y-2 rounded-lg border border-gray-200 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={typeof item.platform === 'string' ? item.platform : 'link'}
                  onChange={(e) => patchAt(index, { platform: e.target.value })}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                >
                  {platforms.map((p) => (
                    <option key={p.v} value={p.v}>
                      {p.l}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40"
                  onClick={() => moveItem(index, 'up')}
                  disabled={index === 0}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-40"
                  onClick={() => moveItem(index, 'down')}
                  disabled={index === items.length - 1}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="ml-auto text-xs text-red-600 hover:text-red-800"
                  onClick={() => removeAt(index)}
                >
                  Supprimer
                </button>
              </div>
              <input
                type="text"
                value={typeof item.label === 'string' ? item.label : ''}
                onChange={(e) => patchAt(index, { label: e.target.value })}
                placeholder="Libellé (accessibilité) — traduisible"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                value={typeof item.href === 'string' ? item.href : ''}
                onChange={(e) => patchAt(index, { href: e.target.value })}
                placeholder="https://… ou modèle avec {{encodedUrl}}"
                className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
              />
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addItem}
          className="rounded-md bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700"
        >
          Ajouter un réseau
        </button>
      </div>
    )
  }

  if (canonical === 'common_module_ref') {
    /** Édition interdite : la référence se pose à l’ajout sur la page ; les textes sont sur la fiche module commun. */
    return null
  }

  // Default: fallback to JSON editor
  return null
}
