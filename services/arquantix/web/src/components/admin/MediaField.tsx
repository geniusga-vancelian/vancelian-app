'use client'

import { useState, useEffect } from 'react'
import { Image as ImageIcon, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaPicker } from './MediaPicker'

interface Media {
  id: string
  key: string
  url: string
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
}

export function MediaField({
  value,
  onChange,
  label = 'Media',
  allowClear = true,
  preview = true,
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

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-gray-700">{label}</label>
      )}

      {selectedMedia && preview ? (
        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
          <div className="flex items-start space-x-4">
            {isImage ? (
              <img
                src={selectedMedia.url}
                alt={selectedMedia.alt || selectedMedia.filename}
                className="w-24 h-24 object-cover rounded border border-gray-200"
              />
            ) : (
              <div className="w-24 h-24 bg-gray-200 rounded border border-gray-300 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-gray-400" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {selectedMedia.filename}
              </p>
              {selectedMedia.width && selectedMedia.height && (
                <p className="text-xs text-gray-500">
                  {selectedMedia.width} × {selectedMedia.height}
                </p>
              )}
            </div>
            {allowClear && (
              <button
                onClick={handleClear}
                className="text-gray-400 hover:text-red-600 transition-colors"
                title="Remove media"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      ) : value && loading ? (
        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 text-sm text-gray-500">
          Loading media info...
        </div>
      ) : (
        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 text-sm text-gray-500">
          No media selected
        </div>
      )}

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => setIsPickerOpen(true)}
        >
          {selectedMedia ? 'Change Media' : 'Select Media'}
        </Button>
        {selectedMedia && allowClear && (
          <Button
            type="button"
            variant="outline"
            onClick={handleClear}
            className="text-red-600 hover:text-red-700"
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









