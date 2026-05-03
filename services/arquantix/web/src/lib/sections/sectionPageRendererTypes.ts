/**
 * Types partagés entre `SectionRenderer` et `mapDataToComponentProps`
 * (évite les imports circulaires).
 */

/** Enregistrement section CMS tel que consommé par le rendu de page. */
export type CmsSectionRecord = {
  id: string
  key: string
  order: number
  schemaVersion: string
  data: any
  locale: string
  status: string
}

export type SectionPageRendererContext = {
  shareSmSection?: CmsSectionRecord | null
}
