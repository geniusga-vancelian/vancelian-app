import { CompanyMapSection } from '@/components/design-system/CompanyMapSection'

export interface SectionCompanyMapProps {
  eyebrow?: string
  title?: string
  description?: string
  backgroundMediaUrl?: string
  backgroundMediaAlt?: string | null
  bodyContent?: string
}

export function SectionCompanyMap({
  eyebrow,
  title,
  description,
  backgroundMediaUrl,
  backgroundMediaAlt,
  bodyContent,
}: SectionCompanyMapProps) {
  return (
    <CompanyMapSection
      eyebrow={eyebrow}
      title={title}
      description={description}
      backgroundImageUrl={backgroundMediaUrl}
      backgroundImageAlt={backgroundMediaAlt}
      bodyContent={bodyContent}
    />
  )
}
