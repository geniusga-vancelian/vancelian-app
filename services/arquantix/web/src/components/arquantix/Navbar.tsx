'use client'

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-neutral-black/80 backdrop-blur-sm border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo wordmark */}
          <div className="flex items-center">
            <img
              src="/logo-arquantix.svg"
              alt="Arquantix"
              className="h-8 md:h-10 text-white"
              style={{ filter: 'invert(1)' }}
            />
          </div>

          {/* Coming Soon Button */}
          <button
            className="bg-brand-bronze hover:opacity-90 text-white px-8 py-3 rounded-full text-sm font-medium transition-opacity tracking-[0.05em] uppercase cursor-default"
            style={{ fontFamily: '"Avenir Next", Avenir, sans-serif' }}
            disabled
          >
            Coming soon
          </button>
        </div>
      </div>
    </nav>
  )
}
