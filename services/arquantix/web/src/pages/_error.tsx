import type { NextPageContext } from 'next'

/**
 * Fallback erreur côté Pages Router : en dev, Next tente de charger `/_error`
 * quand le rendu échoue. Sans ce fichier, le serveur renvoie la page HTML
 * « missing required error components, refreshing... ».
 */
interface ErrorPageProps {
  statusCode?: number
}

export default function ErrorPage({ statusCode }: ErrorPageProps) {
  return (
    <div
      style={{
        fontFamily: 'system-ui, sans-serif',
        padding: '2rem',
        textAlign: 'center',
        maxWidth: 480,
        margin: '0 auto',
      }}
    >
      <h1 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>
        {statusCode ? `Erreur ${statusCode}` : 'Une erreur est survenue'}
      </h1>
      <p style={{ color: '#64748b', fontSize: '0.9375rem' }}>
        Impossible d’afficher cette page pour le moment. Réessayez ou rechargez l’application.
      </p>
    </div>
  )
}

ErrorPage.getInitialProps = ({ res, err }: NextPageContext) => {
  const statusCode =
    res?.statusCode ??
    (err && typeof (err as { statusCode?: number }).statusCode === 'number'
      ? (err as { statusCode: number }).statusCode
      : 404)
  return { statusCode }
}
