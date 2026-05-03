'use client'

import { cn } from '@/lib/utils'
import { figmaDsBodyRootClassName } from '@/components/design-system/extracted/tokens/surfaces'

/**
 * Erreur à la racine (ex. échec partiel du layout) : évite un écran entièrement blanc sans message.
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/error#global-error
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
      <body className={cn(figmaDsBodyRootClassName, 'px-6 py-16 text-neutral-900')}>
        <div className="mx-auto max-w-lg rounded-lg border border-red-200 bg-white p-8 shadow-sm">
          <h1 className="text-lg font-semibold text-red-900">Erreur d’affichage</h1>
          <p className="mt-3 text-sm leading-relaxed text-neutral-600">
            Une erreur critique a interrompu le rendu de la page. Vous pouvez réessayer ou recharger
            l’onglet.
          </p>
          {error.message ? (
            <pre className="mt-4 max-h-40 overflow-auto rounded bg-neutral-50 p-3 text-xs text-neutral-800">
              {error.message}
            </pre>
          ) : null}
          <button
            type="button"
            onClick={reset}
            className="mt-6 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Réessayer
          </button>
        </div>
      </body>
    </html>
  )
}
