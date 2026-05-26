'use client'

import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

type Props = {
  title: string
  description?: string
}

export function PortalPlaceholderScreen({ title, description }: Props) {
  return (
    <PortalPageContainer>
      <div className="mx-auto max-w-2xl">
        <AppEyebrow>Coming soon</AppEyebrow>
        <h1 className="v-h3 m-0 mt-2">{title}</h1>
        {description ? (
          <p className="mt-3 mb-0 font-ui text-[16px] leading-relaxed text-v-fg-body">{description}</p>
        ) : null}
      </div>
    </PortalPageContainer>
  )
}
