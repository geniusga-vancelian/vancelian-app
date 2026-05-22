'use client'

import { deviceFrame } from '@/lib/admin/flutter-preview/tokens'

/**
 * Cadre device (iPhone-like) qui contient l'iframe de preview. Rendu
 * **côté admin** (PAS dans l'iframe). L'iframe interne assure l'isolation
 * de styles entre la page admin (Tailwind, etc.) et la preview (CSS pur DS).
 *
 * Le cadre suit la largeur d'un iPhone 13 mini (375 × 812). On laisse une
 * marge intérieure de 12 px (bezel) pour donner l'impression du chassis.
 */
export function DeviceFrame({
  src,
  title,
}: {
  src: string | null
  title?: string
}) {
  const innerWidth = deviceFrame.width
  const innerHeight = deviceFrame.height
  const bezel = 12
  const outerWidth = innerWidth + bezel * 2
  const outerHeight = innerHeight + bezel * 2

  return (
    <div
      style={{
        width: outerWidth,
        height: outerHeight,
        backgroundColor: deviceFrame.chassis,
        borderRadius: deviceFrame.radius,
        padding: bezel,
        boxShadow:
          '0 30px 60px -20px rgba(15, 23, 42, 0.45), 0 18px 36px -18px rgba(15, 23, 42, 0.35)',
        position: 'relative',
        boxSizing: 'content-box',
      }}
    >
      {/* Notch décorative */}
      <div
        style={{
          position: 'absolute',
          top: bezel + 6,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 110,
          height: 28,
          borderRadius: 16,
          backgroundColor: '#000',
          zIndex: 2,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          width: innerWidth,
          height: innerHeight,
          borderRadius: deviceFrame.radius - bezel,
          overflow: 'hidden',
          backgroundColor: '#F5F5F5',
          position: 'relative',
        }}
      >
        {src ? (
          <iframe
            key={src}
            src={src}
            title={title ?? 'Preview DS Flutter'}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              display: 'block',
            }}
          />
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
              color: '#64748B',
              fontFamily: '"Inter", system-ui, sans-serif',
              fontSize: 14,
              textAlign: 'center',
              lineHeight: '20px',
            }}
          >
            Sélectionnez un nœud dans l’arborescence à gauche pour afficher la
            preview du DS Flutter ici.
          </div>
        )}
      </div>
    </div>
  )
}
