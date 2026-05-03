'use client'

import { useEffect, useState } from 'react'
import { ArrowDown, ArrowUp, FileText, Image as ImageIcon, Plus, RefreshCcw, Video, X } from 'lucide-react'
import { MediaPicker } from '@/components/admin/MediaPicker'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'
import { cn } from '@/lib/utils'

type MediaInfo = {
  id: string
  filename: string
  mimeType: string
  url?: string
}

type MediaTileBaseProps = {
  /** Taille de la vignette (px) — 64 par défaut conformément à la convention densité haute admin. */
  size?: number
  /** Filtre optionnel passé au MediaPicker (ex. "image" pour un carrousel). */
  pickerKind?: 'image' | 'pdf' | 'all'
  /** Titre du modal de sélection. */
  pickerTitle?: string
  /** Désactive entièrement la tuile (lecture seule). */
  disabled?: boolean
  className?: string
}

type MediaTileFilledProps = MediaTileBaseProps & {
  variant?: 'filled'
  mediaId: string
  onChange: (newId: string) => void
  onRemove: () => void
  index: number
  total: number
  onMoveUp?: () => void
  onMoveDown?: () => void
  /** Cache l'étiquette nom de fichier sous la vignette si false. */
  showFilename?: boolean
}

type MediaTileAddProps = MediaTileBaseProps & {
  variant: 'add'
  onSelect: (newId: string) => void
}

type MediaTileProps = MediaTileFilledProps | MediaTileAddProps

const tileBase =
  'group relative flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-gray-200 bg-gray-50 text-gray-500'

/**
 * Vignette compacte (par défaut 64×64) utilisée dans les éditeurs admin pour
 * remplacer les `MediaField` empilés. Action `change`/`remove`/`move` exposée
 * via overlay au survol. Le format de données (`mediaId` string) reste celui
 * actuellement persisté — ce composant n'est qu'une UI alternative.
 */
export function MediaTile(props: MediaTileProps) {
  const size = props.size ?? 64

  if (props.variant === 'add') {
    return <MediaTileAdd {...props} size={size} />
  }

  const { mediaId, onChange, onRemove, index, total, onMoveUp, onMoveDown } = props
  const showFilename = props.showFilename ?? false
  const [info, setInfo] = useState<MediaInfo | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!mediaId) {
      setInfo(null)
      return
    }
    setLoading(true)
    fetch('/api/admin/media')
      .then((r) => (r.ok ? r.json() : { media: [] }))
      .then((d) => {
        if (cancelled) return
        const m = (d.media as MediaInfo[] | undefined)?.find((x) => x.id === mediaId)
        setInfo(m ?? null)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [mediaId])

  const isImage = info?.mimeType?.startsWith('image/')
  const isVideo = info?.mimeType?.startsWith('video/')
  const isPdf = info?.mimeType === 'application/pdf'

  const FallbackIcon = isVideo ? Video : isPdf ? FileText : ImageIcon

  return (
    <div
      className={cn('flex flex-col items-center gap-1', props.className)}
      style={{ width: size }}
    >
      <div
        className={cn(tileBase)}
        style={{ width: size, height: size }}
        title={info?.filename ?? mediaId}
      >
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={adminMediaFileUrl(mediaId)}
            alt={info?.filename ?? ''}
            className="h-full w-full object-cover"
          />
        ) : (
          <FallbackIcon className="h-6 w-6" />
        )}
        {!props.disabled ? (
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-between bg-black/0 p-1 opacity-0 transition group-hover:bg-black/30 group-hover:opacity-100">
            <div className="pointer-events-auto flex justify-end">
              <button
                type="button"
                title="Retirer"
                onClick={(e) => {
                  e.stopPropagation()
                  onRemove()
                }}
                className="rounded bg-white/90 p-0.5 text-red-600 shadow-sm hover:bg-white"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="pointer-events-auto flex items-end justify-between gap-1">
              <div className="flex gap-0.5">
                {onMoveUp ? (
                  <button
                    type="button"
                    title="Déplacer vers la gauche"
                    disabled={index === 0}
                    onClick={(e) => {
                      e.stopPropagation()
                      onMoveUp()
                    }}
                    className="rounded bg-white/90 p-0.5 text-gray-700 shadow-sm hover:bg-white disabled:opacity-40"
                  >
                    <ArrowUp className="h-3 w-3 -rotate-90" />
                  </button>
                ) : null}
                {onMoveDown ? (
                  <button
                    type="button"
                    title="Déplacer vers la droite"
                    disabled={index >= total - 1}
                    onClick={(e) => {
                      e.stopPropagation()
                      onMoveDown()
                    }}
                    className="rounded bg-white/90 p-0.5 text-gray-700 shadow-sm hover:bg-white disabled:opacity-40"
                  >
                    <ArrowDown className="h-3 w-3 -rotate-90" />
                  </button>
                ) : null}
              </div>
              <button
                type="button"
                title="Remplacer le média"
                onClick={(e) => {
                  e.stopPropagation()
                  setPickerOpen(true)
                }}
                className="rounded bg-white/90 p-0.5 text-indigo-700 shadow-sm hover:bg-white"
              >
                <RefreshCcw className="h-3 w-3" />
              </button>
            </div>
          </div>
        ) : null}
      </div>
      {showFilename ? (
        <p
          className="w-full truncate text-center text-[10px] leading-tight text-gray-600"
          title={info?.filename ?? mediaId}
        >
          {loading ? '…' : info?.filename ?? '—'}
        </p>
      ) : null}
      <MediaPicker
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={(media) => {
          onChange(media.id)
          setPickerOpen(false)
        }}
        currentMediaId={mediaId}
        title={props.pickerTitle ?? 'Sélectionner un média'}
      />
    </div>
  )
}

function MediaTileAdd({
  size,
  pickerTitle,
  disabled,
  onSelect,
  className,
}: MediaTileAddProps & { size: number }) {
  const [pickerOpen, setPickerOpen] = useState(false)
  return (
    <div
      className={cn('flex flex-col items-center gap-1', className)}
      style={{ width: size }}
    >
      <button
        type="button"
        disabled={disabled}
        onClick={() => setPickerOpen(true)}
        className={cn(
          'flex shrink-0 items-center justify-center rounded-md border border-dashed border-indigo-300 bg-indigo-50/40 text-indigo-600 transition hover:bg-indigo-50 disabled:opacity-50',
        )}
        style={{ width: size, height: size }}
        title="Ajouter"
      >
        <Plus className="h-5 w-5" />
      </button>
      <MediaPicker
        isOpen={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={(media) => {
          onSelect(media.id)
          setPickerOpen(false)
        }}
        title={pickerTitle ?? 'Ajouter un média'}
      />
    </div>
  )
}
