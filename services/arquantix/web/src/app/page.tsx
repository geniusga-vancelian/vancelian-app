'use client'

import Navbar from '@/components/arquantix/Navbar'
import Hero from '@/components/arquantix/Hero'
import Footer from '@/components/arquantix/Footer'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-neutral-black text-white">
      <Navbar />
      <div className="pt-20">
        <Hero
          images={['/hero.jpg', '/hero-2.jpg']}
          autoplay={true}
          intervalMs={4500}
        />
      </div>
      <Footer />
    </div>
  )
}

