'use client'

import { useState, useEffect } from 'react'
import { Image as ImageIcon, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaPicker } from './MediaPicker'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'

interface Media {
  id: string
  key: string
  url: string
  publicUrl?: string
  filename: string
  mimeType: string
  size: number
  width: number | null
  height: number | null
  alt: string | null
  createdAt: string
}

interface MediaFieldProps {
  value?: string | null
  onChange: (mediaId: string | null) => void
  label?: string
  allowClear?: boolean
  preview?: boolean
  /** Prévisualisation et marges réduites (ex. en-tête à côté d’un titre). */
  compact?: boolean
}

export function MediaField({
  value,
  onChange,
  label = 'Media',
  allowClear = true,
  preview = true,
  compact = false,
}: MediaFieldProps) {
  const [isPickerOpen, setIsPickerOpen] = useState(false)
  const [selectedMedia, setSelectedMedia] = useState<Media | null>(null)
  const [loading, setLoading] = useState(false)

  // Fetch selected media info when value changes
  useEffect(() => {
    if (value) {
      fetchMediaInfo(value)
    } else {
      setSelectedMedia(null)
    }
  }, [value])

  const fetchMediaInfo = async (mediaId: string) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/admin/media`)
      if (response.ok) {
        const data = await response.json()
        const media = data.media?.find((m: Media) => m.id === mediaId)
        if (media) {
          setSelectedMedia(media)
        }
      }
    } catch (error) {
      console.error('Error fetching media info:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (media: Media) => {
    setSelectedMedia(media)
    onChange(media.id)
    setIsPickerOpen(false)
  }

  const handleClear = () => {
    setSelectedMedia(null)
    onChange(null)
  }

  const isImage = selectedMedia?.mimeType.startsWith('image/')

  const thumbClass = compact
    ? 'w-14 h-14 object-cover rounded border border-gray-200 shrink-0'
    : 'w-24 h-24 object-cover rounded border border-gray-200'
  const placeholderBoxClass = compact
    ? 'w-14 h-14 bg-gray-200 rounded border border-gray-300 flex items-center justify-center shrink-0'
    : 'w-24 h-24 bg-gray-200 rounded border border-gray-300 flex items-center justify-center'
  const outerPad = compact ? 'p-2' : 'p-4'
  const rowGap = compact ? 'space-x-2' : 'space-x-4'
  const labelClass = compact
    ? 'block text-xs font-medium text-gray-600'
    : 'block text-sm font-medium text-gray-700'

  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      {label && <label className={labelClass}>{label}</label>}

      {selectedMedia && preview ? (
        <div className={`border border-gray-300 rounded-lg ${outerPad} bg-gray-50`}>
          <div className={`flex items-start ${rowGap}`}>
            {isImage ? (
              <img
                src={adminMediaFileUrl(selectedMedia.id)}
                alt={selectedMedia.alt || selectedMedia.filename}
                className={thumbClass}
              />
            ) : (
              <div className={placeholderBoxClass}>
                <ImageIcon className={`${compact ? 'w-5 h-5' : 'w-8 h-8'} text-gray-400`} />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p
                className={`font-medium text-gray-900 truncate ${compact ? 'text-xs' : 'text-sm'}`}
              >
                {selectedMedia.filename}
              </p>
              {selectedMedia.width && selectedMedia.height && (
                <p className={`text-gray-500 ${compact ? 'text-[10px]' : 'text-xs'}`}>
                  {selectedMedia.width} × {selectedMedia.height}
                </p>
              )}
            </div>
            {allowClear && (
              <button
                onClick={handleClear}
                className={`text-gray-400 hover:text-red-600 transition-colors shrink-0 ${compact ? 'p-0.5' : ''}`}
                title="Remove media"
              >
                <X className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
              </button>
            )}
          </div>
        </div>
      ) : value && loading ? (
        <div
          className={`border border-gray-300 rounded-lg ${outerPad} bg-gray-50 text-gray-500 ${compact ? 'text-xs' : 'text-sm'}`}
        >
          Loading media info...
        </div>
      ) : (
        <div
          className={`border border-gray-300 rounded-lg ${outerPad} bg-gray-50 text-gray-500 ${compact ? 'text-xs' : 'text-sm'}`}
        >
          No media selected
        </div>
      )}

      <div className={`flex flex-wrap gap-2 ${compact ? 'gap-1.5' : ''}`}>
        <Button
          type="button"
          variant="outline"
          size={compact ? 'sm' : 'default'}
          onClick={() => setIsPickerOpen(true)}
          className={compact ? 'text-xs h-8' : undefined}
        >
          {selectedMedia ? 'Change Media' : 'Select Media'}
        </Button>
        {selectedMedia && allowClear && (
          <Button
            type="button"
            variant="outline"
            size={compact ? 'sm' : 'default'}
            onClick={handleClear}
            className={`text-red-600 hover:text-red-700 ${compact ? 'text-xs h-8' : ''}`}
          >
            Remove
          </Button>
        )}
      </div>

      <MediaPicker
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        onSelect={handleSelect}
        currentMediaId={value || undefined}
        title="Select Media"
      />
    </div>
  )
}









