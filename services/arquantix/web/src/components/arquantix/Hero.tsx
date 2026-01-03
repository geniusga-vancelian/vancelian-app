'use client'

import { useState, useEffect, useRef } from 'react'

interface HeroProps {
  images?: string[]
  autoplay?: boolean
  intervalMs?: number
}

export default function Hero({ images, autoplay = true, intervalMs = 4500 }: HeroProps) {
  // Default images if none provided
  const defaultImages = ["/media/hero/slide-1.jpg", "/media/hero/slide-2.jpg"]
  const heroImages = images && images.length > 0 ? images : defaultImages
  const hasMultipleImages = heroImages.length > 1

  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const goToSlide = (index: number) => {
    setCurrentIndex(index)
    resetAutoplay()
  }

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? heroImages.length - 1 : prev - 1))
    resetAutoplay()
  }

  const goToNext = () => {
    setCurrentIndex((prev) => (prev === heroImages.length - 1 ? 0 : prev + 1))
    resetAutoplay()
  }

  const resetAutoplay = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    if (autoplay && hasMultipleImages && !isPaused) {
      startAutoplay()
    }
  }

  const startAutoplay = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    intervalRef.current = setInterval(() => {
      setCurrentIndex((prev) => (prev === heroImages.length - 1 ? 0 : prev + 1))
    }, intervalMs)
  }

  useEffect(() => {
    if (autoplay && hasMultipleImages && !isPaused) {
      startAutoplay()
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoplay, hasMultipleImages, isPaused, intervalMs, heroImages.length])

  return (
    <section
      className="relative w-full h-[660px] flex items-center justify-center overflow-hidden"
      onMouseEnter={() => hasMultipleImages && setIsPaused(true)}
      onMouseLeave={() => hasMultipleImages && setIsPaused(false)}
    >
      {/* Carousel Background Images */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-neutral-black via-[#1a1d24] to-neutral-black z-10" />

        {heroImages.map((imageUrl, index) => (
          <div
            key={index}
            className={`absolute inset-0 bg-cover bg-center transition-opacity duration-[800ms] ease-in-out ${
              index === currentIndex ? 'opacity-100 z-20' : 'opacity-0 z-10'
            }`}
            style={{
              backgroundImage: `url('${imageUrl}')`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
            aria-hidden={index !== currentIndex}
          />
        ))}

        <div className="absolute inset-0 bg-black/60 z-30" />
      </div>

      {/* Navigation Flèches (desktop seulement, si multiple images) */}
      {hasMultipleImages && (
        <>
          <button
            onClick={goToPrevious}
            aria-label="Previous image"
            className="hidden md:flex absolute left-4 md:left-8 z-50 items-center justify-center w-12 h-12 rounded-full bg-black/40 backdrop-blur-sm border border-white/20 text-white hover:bg-black/60 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
          </button>

          <button
            onClick={goToNext}
            aria-label="Next image"
            className="hidden md:flex absolute right-4 md:right-8 z-50 items-center justify-center w-12 h-12 rounded-full bg-black/40 backdrop-blur-sm border border-white/20 text-white hover:bg-black/60 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
          </button>

          {/* Dots Navigation (si multiple images) */}
          <div className="absolute bottom-6 md:bottom-8 left-1/2 transform -translate-x-1/2 z-50 flex gap-2">
            {heroImages.map((_, index) => (
              <button
                key={index}
                onClick={() => goToSlide(index)}
                aria-label={`Go to slide ${index + 1}`}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  index === currentIndex ? 'bg-brand-bronze w-8' : 'bg-white/30 hover:bg-white/50'
                }`}
              />
            ))}
          </div>

          {/* Compteur discret */}
          <div className="absolute bottom-6 md:bottom-8 right-4 md:right-8 z-50 text-white/60 text-xs tracking-wide">
            {currentIndex + 1}/{heroImages.length}
          </div>
        </>
      )}

      {/* Contenu Hero - Centré */}
      <div className="relative z-40 flex flex-col items-center justify-center text-center w-full max-w-[900px] px-6 lg:px-8">
        {/* Titre */}
        <h1
          className="text-white uppercase mb-8 leading-[1.1] tracking-[0.02em] font-light text-2xl md:text-4xl lg:text-5xl xl:text-6xl"
          style={{ fontFamily: "'Avenir', sans-serif" }}
        >
          FRACTIONAL REAL ESTATE,<br />INSTITUTIONAL RIGOR.
        </h1>

        {/* CTA Button */}
        <button
          className="inline-flex items-center justify-center text-white uppercase transition-opacity hover:opacity-90 cursor-default"
          style={{
            fontFamily: "'Avenir', sans-serif",
            fontWeight: 500,
            fontSize: '10px',
            lineHeight: '110%',
            letterSpacing: '0.04em',
            padding: '10px 20px',
            gap: '8px',
            width: '129px',
            height: '36px',
            background: '#C6A47C',
            borderRadius: '20px',
          }}
          disabled
        >
          Coming soon
        </button>
      </div>
    </section>
  )
}
