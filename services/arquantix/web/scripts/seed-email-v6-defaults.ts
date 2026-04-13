/**
 * Seed default Email Modules and Templates for V6
 * Run: npx tsx web/scripts/seed-email-v6-defaults.ts
 */
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

// EmailSpec type definition (inline for seed script)
interface EmailSpec {
  subject: string
  preheader: string | null
  locale: string
  theme: string
  blocks: any[]
}

async function seedEmailV6Defaults() {
  console.log('🌱 Seeding Email V6 defaults (modules + template)...')

  // ============================================================================
  // 1. HEADER DEFAULT
  // ============================================================================
  const headerDefaultSpec: EmailSpec = {
    subject: '',
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'section_title',
        variant: 'centered',
        title: 'ARQUANTIX',
        subtitle: 'Premium insights & projects',
      },
      {
        type: 'divider',
        variant: 'default',
      },
      {
        type: 'spacer',
        variant: 'md',
      },
    ],
  }

  const headerDefault = await prisma.emailModule.upsert({
    where: { slug: 'header_default' },
    update: {
      spec: headerDefaultSpec as any,
      status: 'VALIDATED',
    },
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

  console.log('✅ Created/Updated header_default module')

  // ============================================================================
  // 2. CONTENT DEFAULT (CUSTOM module - base content starter)
  // ============================================================================
  const contentDefaultSpec: EmailSpec = {
    subject: '',
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'hero',
        variant: 'text_only',
        title: 'Welcome to Arquantix',
        subtitle: 'A concise update tailored for you.',
        cta_label: 'Explore',
        cta_url: 'https://arquantix.com',
        image_url: null,
      },
      {
        type: 'text',
        variant: 'body',
        heading: "What's new",
        body: 'Découvrez nos dernières actualités et projets. Nous sommes ravis de partager avec vous les développements récents de notre plateforme.\n\nNotre équipe travaille constamment à améliorer votre expérience et à vous offrir les meilleurs outils pour vos investissements.',
      },
      {
        type: 'feature_cards',
        variant: '3up',
        heading: 'Highlights',
        items: [
          {
            title: 'Nouveaux Projets',
            description: 'Explorez nos dernières opportunités d\'investissement.',
            icon: null,
          },
          {
            title: 'Insights Marché',
            description: 'Analyses et tendances du marché immobilier.',
            icon: null,
          },
          {
            title: 'Performance',
            description: 'Suivez la performance de vos investissements.',
            icon: null,
          },
        ],
      },
      {
        type: 'cta',
        variant: 'primary',
        label: 'Read more',
        url: 'https://arquantix.com',
        hint: null,
      },
      {
        type: 'divider',
        variant: 'default',
      },
    ],
  }

  const contentDefault = await prisma.emailModule.upsert({
    where: { slug: 'content_default' },
    update: {
      spec: contentDefaultSpec as any,
      status: 'VALIDATED',
    },
    create: {
      slug: 'content_default',
      name: 'Content Default',
      description: 'Module de contenu de base avec hero, texte et feature cards',
      moduleType: 'CUSTOM',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      spec: contentDefaultSpec as any,
    },
  })

  console.log('✅ Created/Updated content_default module')

  // ============================================================================
  // 3. FOOTER DEFAULT
  // ============================================================================
  const footerDefaultSpec: EmailSpec = {
    subject: '',
    preheader: null,
    locale: 'fr',
    theme: 'arquantix_v1',
    blocks: [
      {
        type: 'social_icons',
        variant: 'default',
        links: {
          twitter: 'https://twitter.com/arquantix',
          linkedin: 'https://linkedin.com/company/arquantix',
        },
        size: 'sm',
      },
      {
        type: 'text',
        variant: 'body',
        heading: null,
        body: 'Si vous ne souhaitez plus recevoir d\'e-mails de la part d\'Arquantix, vous pouvez vous désinscrire ici : {{unsubscribe_url}}.',
      },
      {
        type: 'text',
        variant: 'body',
        heading: null,
        body: 'Nous traitons vos Informations Personnelles conformément à notre Politique de Confidentialité : {{privacy_policy_url}}.',
      },
      {
        type: 'text',
        variant: 'body',
        heading: null,
        body: 'Les informations fournies sont à titre informatif et ne constituent pas un conseil en investissement. Les actifs numériques et investissements peuvent comporter des risques. Investissez uniquement ce que vous pouvez vous permettre de perdre.',
      },
      {
        type: 'footer',
        variant: 'default',
        company_name: 'Arquantix',
        address: '123 Avenue de l\'Investissement, 75001 Paris, France',
        unsubscribe_url_placeholder: '{{unsubscribe_url}}',
      },
      {
        type: 'text',
        variant: 'body',
        heading: null,
        body: '© 2026 Arquantix. Tous droits réservés.',
      },
    ],
  }

  const footerDefault = await prisma.emailModule.upsert({
    where: { slug: 'footer_default' },
    update: {
      spec: footerDefaultSpec as any,
      status: 'VALIDATED',
    },
    create: {
      slug: 'footer_default',
      name: 'Footer Default',
      description: 'Pied de page par défaut avec mentions légales, désinscription et copyright Arquantix',
      moduleType: 'FOOTER',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      spec: footerDefaultSpec as any,
    },
  })

  console.log('✅ Created/Updated footer_default module')

  // ============================================================================
  // 4. BASE TEMPLATE (uses all 3 modules)
  // ============================================================================
  const baseTemplate = await prisma.emailTemplateEntity.upsert({
    where: { slug: 'base_v1_db' },
    update: {
      headerModuleId: headerDefault.id,
      footerModuleId: footerDefault.id,
      bodyStarterModuleId: contentDefault.id,
      fixedModuleIds: null,
      status: 'VALIDATED',
    },
    create: {
      slug: 'base_v1_db',
      name: 'Base Template (DB)',
      description: 'Template de base utilisant les modules header_default, footer_default avec content_default comme body starter',
      theme: 'arquantix_v1',
      status: 'VALIDATED',
      heroPolicy: 'REQUIRED',
      headerModuleId: headerDefault.id,
      footerModuleId: footerDefault.id,
      bodyStarterModuleId: contentDefault.id,
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
              image_url: null,
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
            type: 'cta',
            variant: 'primary',
            props: {
              label: '',
              url: '',
              hint: null,
            },
          },
        ],
        optional_slots: {
          TEXT_body: { max: 3 },
          BULLETS_default: { max: 2 },
          IMAGE_contained: { max: 2 },
          DIVIDER_default: { max: 2 },
          SPACER_md: { max: 2 },
        },
      },
      lockPolicy: {
        core_blocks: [
          { type: 'hero', variant: 'text_only' },
          { type: 'text', variant: 'body' },
          { type: 'cta', variant: 'primary' },
        ],
        optional_slots: {
          TEXT_body: { max: 3 },
          BULLETS_default: { max: 2 },
          IMAGE_contained: { max: 2 },
          DIVIDER_default: { max: 2 },
          SPACER_md: { max: 2 },
        },
      },
    },
  })

  console.log('✅ Created/Updated base_v1_db template')

  console.log('✨ Email V6 defaults seeding completed!')
  console.log(`   - Modules: header_default, content_default, footer_default`)
  console.log(`   - Template: base_v1_db`)
}

async function main() {
  try {
    await seedEmailV6Defaults()
  } catch (error) {
    console.error('❌ Error seeding email V6 defaults:', error)
    throw error
  } finally {
    await prisma.$disconnect()
  }
}

if (require.main === module) {
  main()
}

export { seedEmailV6Defaults }

