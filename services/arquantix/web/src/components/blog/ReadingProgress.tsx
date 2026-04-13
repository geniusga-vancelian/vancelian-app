'use client'

import { useEffect, useState } from 'react'

export function ReadingProgress() {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const updateProgress = () => {
      const windowHeight = window.innerHeight
      const documentHeight = document.documentElement.scrollHeight
      const scrollTop = window.scrollY || document.documentElement.scrollTop
      const scrollableHeight = documentHeight - windowHeight
      const progressPercent = scrollableHeight > 0 ? (scrollTop / scrollableHeight) * 100 : 0
      setProgress(Math.min(100, Math.max(0, progressPercent)))
    }

    const handleScroll = () => {
      requestAnimationFrame(updateProgress)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    updateProgress() // Initial update

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  return (
    <div className="fixed top-0 left-0 right-0 h-1 bg-gray-200 z-50">
      <div
        className="h-full bg-indigo-600 transition-all duration-150 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}









