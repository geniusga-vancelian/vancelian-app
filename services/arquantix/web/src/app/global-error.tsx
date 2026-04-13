'use client'

/**
 * Erreurs dans le layout racine : `error.tsx` ne suffit pas sans `global-error.tsx`
 * car le root layout n’a pas de boundary parent.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="fr">
      <body>
        <div
          style={{
            fontFamily: 'system-ui, sans-serif',
            padding: '2rem',
            textAlign: 'center',
            maxWidth: 480,
            margin: '4rem auto',
          }}
        >
          <h1 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Une erreur est survenue</h1>
          <p style={{ color: '#64748b', fontSize: '0.9375rem', marginBottom: '1.5rem' }}>
            {error.message || 'Erreur inattendue'}
          </p>
          <button
            type="button"
            onClick={() => reset()}
            style={{
              padding: '0.5rem 1.25rem',
              backgroundColor: '#4f46e5',
              color: '#fff',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.9375rem',
            }}
          >
            Réessayer
          </button>
        </div>
      </body>
    </html>
  )
}
