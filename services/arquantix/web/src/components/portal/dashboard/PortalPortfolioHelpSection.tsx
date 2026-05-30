import { AppAdvisorMultichannelCard } from '@/components/design-system/app/AppAdvisorMultichannelCard'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'

/** “Need help?” block — handoff Portfolio.html. */
export function PortalPortfolioHelpSection() {
  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader
        title="Need help?"
        size="lg"
        desc="Our team typically responds within one business hour."
      />
      <AppAdvisorMultichannelCard />
    </section>
  )
}
