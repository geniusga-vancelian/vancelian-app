'use client'

import { useState } from 'react'

type AdminLogin0BackgroundProps = {
  /** URL absolue du fichier vidéo (mp4/webm). Si absent ou erreur de lecture : fond dégradé uniquement (pas d’image). */
  videoUrl?: string
}

function Login0FallbackBackground() {
  return (
    <div
      className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-black"
      aria-hidden
    />
  )
}

/**
 * Fond plein écran pour /admin/login0 — vidéo plein écran ou dégradé si pas de média / erreur.
 */
export function AdminLogin0Background({ videoUrl }: AdminLogin0BackgroundProps) {
  const [mediaReady, setMediaReady] = useState(false)
  const trimmed = videoUrl?.trim()
  const [useFallback, setUseFallback] = useState(!trimmed)

  if (useFallback || !trimmed) {
    return <Login0FallbackBackground />
  }

  return (
    <div className="absolute inset-0 z-0 w-full overflow-hidden">
      <video
        className="absolute inset-0 h-full w-full object-cover object-center"
        src={trimmed}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden
        onLoadedData={() => setMediaReady(true)}
        onCanPlay={() => setMediaReady(true)}
        onError={() => setUseFallback(true)}
      />
      {!mediaReady && (
        <div
          className="absolute inset-0 z-[1] bg-slate-950 animate-pulse"
          aria-hidden
        />
      )}
    </div>
  )
}
