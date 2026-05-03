import Link from 'next/link'
import { Palette, LayoutTemplate, Boxes, Wand2, ArrowRight, Mail } from 'lucide-react'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Email — Hub MJML',
}

const HUB_CARDS = [
  {
    href: '/admin/email/design',
    icon: Palette,
    color: 'bg-pink-50 text-pink-600',
    title: 'Design System',
    description:
      'Tokens (couleurs, typo, layout), atomes, headers, footer, preview React inline + onglet MJML production.',
  },
  {
    href: '/admin/email/templates',
    icon: LayoutTemplate,
    color: 'bg-purple-50 text-purple-600',
    title: 'Templates MJML',
    description:
      '4 templates production-ready (Newsletter, OTP, Transactionnel, Welcome). Variables Zod, fixtures, preview FR/EN.',
  },
  {
    href: '/admin/email/components',
    icon: Boxes,
    color: 'bg-emerald-50 text-emerald-600',
    title: 'Components MJML',
    description:
      '16 composants réutilisables (HeaderL1/L2/L3, Footer, Card, CTASection, OTPCode, Button…). Preview standalone.',
  },
  {
    href: '/admin/email/ai-builder',
    icon: Wand2,
    color: 'bg-blue-50 text-blue-600',
    title: 'AI Builder',
    description:
      'Chat IA (OpenAI) qui génère un email à partir d’un template MJML, avec preview live. Validation Zod stricte.',
  },
] as const

const LEGACY_CARDS = [
  {
    href: '/admin/ai/email',
    title: 'Email Builder (legacy IA chat)',
    description:
      'Ancien Copilot IA basé sur EmailSpec + buildMjml + backend FastAPI. Conservé pour compatibilité.',
  },
  {
    href: '/admin/email-templates',
    title: 'Email Templates DB',
    description:
      'Templates stockés en base (Prisma) avec modules header/footer DB et politique de lock.',
  },
  {
    href: '/admin/email-modules',
    title: 'Email Modules DB',
    description:
      'Modules réutilisables stockés en base (Prisma) avec gestion des traductions par locale.',
  },
  {
    href: '/admin/emails',
    title: 'Emails (drafts validés)',
    description: 'Liste des e-mails composés (drafts / validated) sauvegardés via le builder legacy.',
  },
] as const

export default function EmailHubPage() {
  return (
    <div className="space-y-10 max-w-6xl">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-gray-500 mb-2">
            <Mail className="w-3.5 h-3.5" />
            Email — pipeline MJML
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Hub Email</h1>
          <p className="text-sm text-gray-600 mt-1 max-w-2xl">
            Tout le système email Arquantix : design system, templates, composants
            réutilisables et builder IA. Pipeline strict (MJML 5 in-process + Mustache
            + Zod), 100% indépendant des modules legacy stockés en base.
          </p>
        </div>
      </div>

      <section>
        <h2 className="text-xs uppercase tracking-wide text-gray-500 mb-3">
          Système MJML (production)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {HUB_CARDS.map(({ href, icon: Icon, color, title, description }) => (
            <Link
              key={href}
              href={href}
              className="group relative bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg hover:border-gray-300 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`p-2.5 rounded-lg ${color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-700 transition-colors" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xs uppercase tracking-wide text-gray-500 mb-3">
          Système legacy (conservé, non destructif)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {LEGACY_CARDS.map(({ href, title, description }) => (
            <Link
              key={href}
              href={href}
              className="group flex items-start justify-between gap-4 bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300 hover:shadow-sm transition-all"
            >
              <div>
                <div className="text-sm font-semibold text-gray-900">{title}</div>
                <div className="text-xs text-gray-500 mt-0.5">{description}</div>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-700 mt-0.5 shrink-0" />
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-gray-50 border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Commandes utiles</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-white border border-gray-200 rounded-md p-3">
            <div className="text-gray-500 uppercase tracking-wide mb-1">Build emails</div>
            <code className="font-mono">npm run emails:build</code>
          </div>
          <div className="bg-white border border-gray-200 rounded-md p-3">
            <div className="text-gray-500 uppercase tracking-wide mb-1">Server preview</div>
            <code className="font-mono">npm run emails:preview</code>
          </div>
          <div className="bg-white border border-gray-200 rounded-md p-3">
            <div className="text-gray-500 uppercase tracking-wide mb-1">Validate strict</div>
            <code className="font-mono">npm run emails:validate</code>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          Documentation complète :{' '}
          <code className="font-mono">docs/EMAIL_MJML.md</code>
        </p>
      </section>
    </div>
  )
}
