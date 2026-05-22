import { VSecurity } from '@/components/design-system/vancelian/VSecurity'

export interface SectionSecurityProps {
  eyebrow?: string
  title?: string
  description?: string
  points?: Array<{ text: string }>
  linkText?: string
  linkHref?: string
  logos?: Array<{ label: string; caption?: string }>
}

export function SectionSecurity(props: SectionSecurityProps) {
  return <VSecurity {...props} />
}
