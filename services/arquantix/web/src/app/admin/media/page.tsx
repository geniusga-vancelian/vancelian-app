'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, Search, Copy, Trash2, Image as ImageIcon, Loader2, FileText, Video } from 'lucide-react'
import { Button } from '@/components/ui/button'

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
  uploadedBy: {
    id: string
    email: string
  } | null
}

export default function AdminMediaPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [media, setMedia] = useState<Media[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'images' | 'videos' | 'documents'>('all')

  useEffect(() => {
    fetchMedia()
  }, [search])

  const fetchMedia = async () => {
    setLoading(true)
    setError(null)
    const ac = new AbortController()
    const t = setTimeout(() => ac.abort(), 45_000)
    try {
      const url = search
        ? `/api/admin/media?search=${encodeURIComponent(search)}`
        : '/api/admin/media'
      const response = await fetch(url, {
        credentials: 'include',
        signal: ac.signal,
      })
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch media')
      }
      const data = await response.json()
      setMedia(data.media || [])
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setError('Délai dépassé : vérifie que Next.js tourne et que la base répond.')
      } else {
        setError(e.message || 'Failed to load media')
      }
    } finally {
      clearTimeout(t)
      setLoading(false)
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/admin/media/upload', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.error || `Upload failed: ${response.status} ${response.statusText}`)
      }

      const result = await response.json()
      
      // Clear input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      // Refresh list
      await fetchMedia()
    } catch (e: any) {
      console.error('Upload error:', e)
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (mediaId: string) => {
    if (!confirm('Are you sure you want to delete this media?')) {
      return
    }

    try {
      const response = await fetch(`/api/admin/media/${mediaId}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Delete failed')
      }

      await fetchMedia() // Refresh list
    } catch (e: any) {
      setError(e.message || 'Delete failed')
    }
  }

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    setCopiedUrl(url)
    setTimeout(() => setCopiedUrl(null), 2000)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getMediaType = (mimeType: string): 'image' | 'video' | 'document' => {
    if (mimeType.startsWith('image/')) return 'image'
    if (mimeType.startsWith('video/')) return 'video'
    return 'document'
  }

  const filteredMedia = media.filter((item) => {
    if (activeTab === 'all') return true
    const type = getMediaType(item.mimeType)
    return (
      (activeTab === 'images' && type === 'image') ||
      (activeTab === 'videos' && type === 'video') ||
      (activeTab === 'documents' && type === 'document')
    )
  })

  const imagesCount = media.filter((item) => getMediaType(item.mimeType) === 'image').length
  const videosCount = media.filter((item) => getMediaType(item.mimeType) === 'video').length
  const documentsCount = media.filter((item) => getMediaType(item.mimeType) === 'document').length

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Media Library</h1>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelected}
            accept="image/*,application/pdf,video/mp4,video/webm"
            className="hidden"
            disabled={uploading}
          />
          <Button 
            type="button" 
            onClick={handleUploadClick}
            disabled={uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Upload Media
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('all')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'all'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              All ({media.length})
            </button>
            <button
              onClick={() => setActiveTab('images')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'images'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <ImageIcon className="w-4 h-4" />
              1. Images ({imagesCount})
            </button>
            <button
              onClick={() => setActiveTab('videos')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'videos'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Video className="w-4 h-4" />
              2. Videos ({videosCount})
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'documents'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileText className="w-4 h-4" />
              3. Documents ({documentsCount})
            </button>
          </nav>
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search media by filename or alt text..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md flex items-center justify-between">
          <span>Error: {error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 ml-4"
          >
            ×
          </button>
        </div>
      )}

      {/* Media Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading media...</div>
      ) : filteredMedia.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          {activeTab === 'images' && <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'videos' && <Video className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'documents' && <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          {activeTab === 'all' && <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />}
          <p className="text-gray-600 mb-2">No {activeTab === 'all' ? 'media' : activeTab} found</p>
          <p className="text-sm text-gray-500">
            {search ? 'Try a different search term.' : 'Upload your first file to get started.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {filteredMedia.map((item) => {
            const mediaType = getMediaType(item.mimeType)
            const isImage = mediaType === 'image'
            const isVideo = mediaType === 'video'
            const isDocument = mediaType === 'document'

            return (
              <div
                key={item.id}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
              >
                {isImage ? (
                  <img
                    src={item.url}
                    alt={item.alt || item.filename}
                    className="w-full h-48 object-cover"
                  />
                ) : isVideo ? (
                  <div className="w-full h-48 bg-gray-900 flex items-center justify-center relative">
                    <video
                      src={item.url}
                      className="w-full h-full object-contain"
                      controls={false}
                      preload="metadata"
                    />
                    <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                      <Video className="w-12 h-12 text-white opacity-80" />
                    </div>
                  </div>
                ) : isDocument ? (
                  <div className="w-full h-48 bg-gray-50 flex flex-col items-center justify-center border-b border-gray-200">
                    <FileText className="w-16 h-16 text-red-600 mb-2" />
                    <div className="px-3 py-1 bg-white rounded border border-gray-200 text-xs text-gray-700 font-medium">
                      PDF
                    </div>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 text-xs text-indigo-600 hover:text-indigo-800 underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Preview PDF
                    </a>
                  </div>
                ) : (
                  <div className="w-full h-48 bg-gray-100 flex items-center justify-center">
                    <FileText className="w-12 h-12 text-gray-400" />
                  </div>
                )}
                <div className="p-3">
                  <p className="text-sm font-medium text-gray-900 truncate mb-1">
                    {item.filename}
                  </p>
                  <p className="text-xs text-gray-500 mb-2">
                    {formatFileSize(item.size)}
                    {item.width && item.height && ` • ${item.width}×${item.height}`}
                    {isDocument && ' • PDF'}
                  </p>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleCopyUrl(item.url)}
                      className="flex-1 text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center justify-center"
                      title="Copy URL"
                    >
                      <Copy className="w-3 h-3 mr-1" />
                      {copiedUrl === item.url ? 'Copied!' : 'Copy URL'}
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="px-2 py-1 text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

