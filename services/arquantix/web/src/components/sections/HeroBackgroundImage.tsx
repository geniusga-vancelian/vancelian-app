'use client'

import { useState, useEffect } from 'react'

interface HeroBackgroundImageProps {
  src: string
}

export function HeroBackgroundImage({ src }: HeroBackgroundImageProps) {
  const [imageError, setImageError] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[HeroBackgroundImage] Loading image:', src)
    }
  }, [src])

  if (!src || src.trim() === '' || imageError) {
    return <div className="w-full h-full bg-black" />
  }

  return (
    <div className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
      <img
        src={src}
        alt=""
        className="w-full h-full object-cover"
        style={{ display: 'block', position: 'absolute', inset: 0 }}
        onError={() => {
          console.error('[HeroBackgroundImage] Image failed to load:', src)
          setImageError(true)
        }}
        onLoad={() => {
          if (process.env.NODE_ENV === 'development') {
            console.log('[HeroBackgroundImage] Image loaded successfully:', src)
          }
          setImageLoaded(true)
        }}
      />
      {!imageLoaded && !imageError && (
        <div className="absolute inset-0 bg-black animate-pulse" style={{ zIndex: 1 }} />
      )}
    </div>
  )
}

