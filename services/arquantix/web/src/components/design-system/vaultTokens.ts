import { cn } from '@/lib/utils'

/** Titre de module vault — échelle éditoriale DS (module). */
export const VAULT_MODULE_TITLE_TYPO =
  'font-ui text-[clamp(28px,3vw,40px)] font-semibold leading-[1.1] tracking-normal text-center text-v-fg'

/** Alias historique — même échelle que {@link VAULT_MODULE_TITLE_TYPO}. */
export const SIMPLE_MARKDOWN_MODULE_TITLE_TYPO = VAULT_MODULE_TITLE_TYPO

/** Chapô / intro sous-titre de module. */
export const VAULT_MODULE_DESCRIPTION_TYPO =
  'font-ui text-[18px] leading-relaxed text-v-fg-body text-center'

/** Corps markdown long (SimpleMarkdownContentModule). */
export const VAULT_MODULE_MARKDOWN_BODY_TYPO =
  'font-ui text-[18px] leading-relaxed text-v-fg-body'

/** Corps PARAGRAPH / listes numérotées (aligné articles). */
export const VAULT_PARAGRAPH_BODY_READING_TYPO =
  'font-ui text-[17px] font-normal leading-relaxed tracking-normal text-v-fg-body md:text-[18px]'

/** Carte module DS standard. */
export const VAULT_MODULE_CARD_CLASS =
  'rounded-v-card border border-v-fg-10 bg-v-card p-6 shadow-v-subtle md:p-8'

/** Ligne zébrée paire. */
export const VAULT_MODULE_STRIPE_EVEN = 'bg-v-card'

/** Ligne zébrée impaire. */
export const VAULT_MODULE_STRIPE_ODD = 'bg-v-bg-warm'

/** Lien texte DS. */
export const VAULT_MODULE_LINK_CLASS =
  'v-text-link font-ui text-[14px] font-medium no-underline hover:underline'

/** CTA pill primaire. */
export const VAULT_MODULE_CTA_CLASS =
  'inline-flex min-h-[44px] items-center justify-center rounded-v-pill bg-v-fg px-10 py-3 font-ui text-xs font-semibold uppercase tracking-v-wide text-white transition-opacity hover:opacity-90 no-underline'

/** Titre intercalé (HEADING blog-style). */
export const VAULT_MODULE_HEADING_CLASS =
  'font-ui text-[26px] font-semibold leading-[1.1] text-v-fg scroll-mt-28 mt-10 first:mt-0 md:text-[28px]'

/** Conteneur média (iframe, vidéo). */
export const VAULT_MODULE_MEDIA_FRAME_CLASS =
  'overflow-hidden rounded-v-card border border-v-fg-10 bg-v-fg-05 shadow-v-subtle'

/** Image galerie. */
export const VAULT_MODULE_IMAGE_CLASS =
  'overflow-hidden rounded-v-card bg-v-fg-05'

export function vaultStripeClass(index: number): string {
  return index % 2 === 0 ? VAULT_MODULE_STRIPE_EVEN : VAULT_MODULE_STRIPE_ODD
}

export function vaultProseMarkdownClass(extra?: string): string {
  return cn(
    'prose prose-neutral w-full max-w-none text-justify',
    VAULT_MODULE_MARKDOWN_BODY_TYPO,
    'prose-p:my-3 prose-p:text-justify prose-p:text-inherit',
    'prose-li:text-inherit prose-strong:text-inherit prose-a:v-text-link prose-a:no-underline hover:prose-a:underline',
    extra,
  )
}
