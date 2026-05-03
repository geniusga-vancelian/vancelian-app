/**
 * Zone réservée dans l’aperçu public des gabarits CMS (article / offre exclusive) :
 * le contenu Prisma (article) ou Vault (offre) n’existe pas sur la page gabarit seule.
 */
export function GabaritPreviewPlaceholder({
  variant,
}: {
  variant: 'article' | 'exclusive_offer'
}) {
  const isArticle = variant === 'article'
  return (
    <section
      className="my-8 rounded-xl border-2 border-dashed border-amber-400/90 bg-amber-50/60 px-5 py-6 shadow-sm sm:px-8 sm:py-8"
      aria-label={isArticle ? 'Emplacement contenu article' : 'Emplacement contenu offre exclusive'}
    >
      <h2 className="text-base font-semibold tracking-tight text-amber-950 sm:text-lg">
        {isArticle ? 'Info de l’article' : 'Info de l’offre exclusive'}
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-amber-950/85">
        {isArticle
          ? 'Sur un article publié, cette zone affiche le lecteur (titre, chapô, médias, corps, documents, etc.). Ici vous voyez uniquement le gabarit : les autres modules CMS autour sont rendus normalement.'
          : 'Sur une page offre (`/projects/…`), cette zone affiche le détail Vault Builder (modules, médias, données produit). Ici vous voyez uniquement le gabarit : les blocs CMS périphériques sont rendus comme en production.'}
      </p>
    </section>
  )
}
