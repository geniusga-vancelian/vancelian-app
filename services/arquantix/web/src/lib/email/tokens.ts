/**
 * Re-export typé des tokens e-mail depuis `emails/mjml/tokens/` (source unique).
 *
 * Pourquoi ce fichier ?
 * - Évite que d’autres modules `src/` aient besoin d’écrire `@/../emails/...`
 *   (chemin relatif fragile, hors du root TypeScript).
 * - Garde une **seule source de vérité** : si on update `colors.json`,
 *   `typography.json` ou `layout.json`, tous les consommateurs (composants
 *   MJML au build, builder v2 `buildMjmlV2`, DS React `email-ds/`) suivent.
 */
export { emailTokens } from '@/../emails/mjml/tokens'
export type { EmailTokens } from '@/../emails/mjml/tokens'
