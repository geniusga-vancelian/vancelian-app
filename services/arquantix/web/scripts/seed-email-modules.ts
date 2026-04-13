/**
 * Seed default Email Modules
 * Run: npx tsx web/scripts/seed-email-modules.ts
 */
import { PrismaClient } from '@prisma/client'

// EmailSpec type definition (inline for seed script)
interface EmailSpec {
  subject: string
  preheader: string | null
  locale: string
  theme: string
  blocks: any[]
}

const prisma = new PrismaClient()

async function seedEmailModules() {
  console.log('🌱 Seeding email modules...')

  // 1. Header Default
  const headerDefaultSpec: EmailSpec = {
    subject: '', // Not used in modules
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'section_title',
        variant: 'centered',
        title: 'ARQUANTIX',
        subtitle: 'Votre plateforme d\'investissement de confiance',
      },
      {
        type: 'divider',
        variant: 'default',
      },
    ],
  }

  const headerDefault = await prisma.emailModule.upsert({
    where: { slug: 'header_default' },
    update: {},
    create: {
      slug: 'header_default',
      name: 'Header Default',
      description: 'En-tête par défaut Arquantix avec logo et sous-titre',
      moduleType: 'HEADER',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      spec: headerDefaultSpec as any,
    },
  })

  console.log('✅ Created header_default module')

  // 2. Footer Default
  const footerDefaultSpec: EmailSpec = {
    subject: '',
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'text',
        variant: 'body',
        body: '© 2025 Arquantix. Tous droits réservés.',
      },
      {
        type: 'text',
        variant: 'body',
        body: 'Cette adresse email est utilisée pour envoyer des communications importantes. Si vous ne souhaitez plus recevoir ces emails, vous pouvez vous désabonner.',
      },
      {
        type: 'footer',
        variant: 'default',
        company_name: 'Arquantix',
        address: '123 Avenue de l\'Investissement, 75001 Paris, France',
        unsubscribe_url_placeholder: '{{unsubscribe_url}}',
      },
    ],
  }

  const footerDefault = await prisma.emailModule.upsert({
    where: { slug: 'footer_default' },
    update: {},
    create: {
      slug: 'footer_default',
      name: 'Footer Default',
      description: 'Pied de page par défaut avec informations légales et lien de désinscription',
      moduleType: 'FOOTER',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      spec: footerDefaultSpec as any,
    },
  })

  console.log('✅ Created footer_default module')

  // 3. Footer Investor
  const footerInvestorSpec: EmailSpec = {
    subject: '',
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'text',
        variant: 'body',
        body: '© 2025 Arquantix. Tous droits réservés.',
      },
      {
        type: 'text',
        variant: 'body',
        body: 'Ce message est destiné exclusivement aux investisseurs. Les informations contenues dans cet email sont confidentielles et ne doivent pas être partagées.',
      },
      {
        type: 'bullets',
        variant: 'default',
        heading: 'Informations importantes',
        items: [
          'Conformément à la réglementation en vigueur',
          'Documents disponibles sur votre espace investisseur',
          'Contact: investisseurs@arquantix.com',
        ],
      },
      {
        type: 'footer',
        variant: 'default',
        company_name: 'Arquantix',
        address: '123 Avenue de l\'Investissement, 75001 Paris, France',
        unsubscribe_url_placeholder: '{{unsubscribe_url}}',
      },
    ],
  }

  const footerInvestor = await prisma.emailModule.upsert({
    where: { slug: 'footer_investor' },
    update: {},
    create: {
      slug: 'footer_investor',
      name: 'Footer Investor',
      description: 'Pied de page spécifique pour les communications investisseurs avec mentions réglementaires',
      moduleType: 'FOOTER',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      spec: footerInvestorSpec as any,
    },
  })

  console.log('✅ Created footer_investor module')

  // 4. Create welcome_v1_db template using header_default + footer_default
  const welcomeTemplate = await prisma.emailTemplateEntity.upsert({
    where: { slug: 'welcome_v1_db' },
    update: {},
    create: {
      slug: 'welcome_v1_db',
      name: 'Welcome Email (DB)',
      description: 'Email de bienvenue utilisant les modules header_default et footer_default',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      heroPolicy: 'REQUIRED',
      headerModuleId: headerDefault.id,
      footerModuleId: footerDefault.id,
      fixedModuleIds: null,
      bodyTemplate: {
        core_blocks: [
          {
            type: 'hero',
            variant: 'text_only',
            props: {
              title: '',
              subtitle: '',
              cta_label: '',
              cta_url: '',
            },
          },
          {
            type: 'text',
            variant: 'body',
            props: {
              heading: '',
              body: '',
            },
          },
          {
            type: 'feature_cards',
            variant: '3up',
            props: {
              heading: '',
              items: [],
            },
          },
          {
            type: 'cta',
            variant: 'primary',
            props: {
              label: '',
              url: '',
              hint: '',
            },
          },
        ],
        optional_slots: {
          IMAGE_contained: { max: 1 },
          DIVIDER_default: { max: 2 },
          SPACER_md: { max: 2 },
        },
      },
      lockPolicy: {
        core_blocks: [
          { type: 'hero', variant: 'text_only' },
          { type: 'text', variant: 'body' },
          { type: 'feature_cards', variant: '3up' },
          { type: 'cta', variant: 'primary' },
        ],
        optional_slots: {
          IMAGE_contained: { max: 1 },
          DIVIDER_default: { max: 2 },
          SPACER_md: { max: 2 },
        },
      },
    },
  })

  console.log('✅ Created welcome_v1_db template')

  console.log('✨ Email modules seeding completed!')
}

async function main() {
  try {
    await seedEmailModules()
  } catch (error) {
    console.error('Error seeding email modules:', error)
    throw error
  } finally {
    await prisma.$disconnect()
  }
}

if (require.main === module) {
  main()
}

export { seedEmailModules }

