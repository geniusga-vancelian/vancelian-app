'use client'

export default function Footer() {
  return (
    <footer
      className="bg-neutral-black"
      style={{
        padding: '120px 64px',
        gap: '40px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '572.33px',
      }}
    >
      <div
        className="flex flex-col items-center"
        style={{
          gap: '96px',
          width: '100%',
          maxWidth: '1152px',
        }}
      >
        {/* Logo */}
        <div className="flex justify-center">
          <img
            src="/media/logo/arquantix.svg"
            alt="Arquantix"
            style={{
              width: '203px',
              height: '44.33px',
              filter: 'invert(1)',
            }}
          />
        </div>

        {/* Copyright */}
        <div
          className="text-center"
          style={{
            fontFamily: "'Avenir', sans-serif",
            fontWeight: 350,
            fontSize: '14px',
            lineHeight: '160%',
            color: '#E6E6E6',
            width: '100%',
            maxWidth: '1152px',
            height: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          © Arquantix — All rights reserved
        </div>
      </div>
    </footer>
  )
}
