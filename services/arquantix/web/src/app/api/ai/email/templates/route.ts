import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

// Single golden template - arquantix_ugg_v1
const UGG_TEMPLATE = [
  {
    id: 'arquantix_ugg_v1',
    name: 'Arquantix UGG v1',
    description: 'Single golden template based on UGG-style MJML. AI generates JSON only.',
    locked: false,
    source: 'hardcoded' as const,
  },
]

// Legacy templates (archived, only shown if SHOW_LEGACY_TEMPLATES=true)
const LEGACY_TEMPLATES = [
  {
    id: 'welcome_v1',
    name: 'Welcome Email',
    description: 'Welcome new users with an introduction and key features',
    locked: true,
    source: 'hardcoded' as const,
  },
  {
    id: 'newsletter_v1',
    name: 'Newsletter',
    description: 'Monthly newsletter with market updates and insights',
    locked: true,
    source: 'hardcoded' as const,
  },
  {
    id: 'project_update_v1',
    name: 'Project Update',
    description: 'Announce new features and platform updates',
    locked: true,
    source: 'hardcoded' as const,
  },
  {
    id: 'investor_update_v1',
    name: 'Investor Update',
    description: 'Quarterly performance summary for investors',
    locked: true,
    source: 'hardcoded' as const,
  },
]

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    
    // Check if legacy templates should be shown
    const showLegacy = process.env.SHOW_LEGACY_TEMPLATES === 'true'
    const url = new URL(request.url)
    const showLegacyParam = url.searchParams.get('show_legacy') === 'true'
    
    if (showLegacy || showLegacyParam) {
      // Return legacy templates if enabled
      return NextResponse.json(LEGACY_TEMPLATES)
    }

    // By default, return only the UGG template
    if (!session) {
      // Return UGG template even if not authenticated (for better UX)
      console.warn('Unauthorized request to templates, returning UGG template')
      return NextResponse.json(UGG_TEMPLATE)
    }

    // Fetch DB templates (VALIDATED only) - but we only use UGG now
    const dbTemplates = await prisma.emailTemplateEntity.findMany({
      where: {
        status: 'VALIDATED',
        slug: 'arquantix_ugg_v1_db', // Only fetch UGG template from DB if it exists
      },
      select: {
        id: true,
        slug: true,
        name: true,
        description: true,
      },
    }).catch((err) => {
      console.error('Error fetching DB templates:', err)
      return [] // Return empty array on error
    })

    // Merge UGG template (hardcoded takes precedence)
    const allTemplates = [
      ...UGG_TEMPLATE,
      ...dbTemplates.map((t) => ({
        id: t.slug,
        name: t.name,
        description: t.description || '',
        locked: false,
        source: 'db' as const,
      })),
    ]

    // Always return at least UGG template
    return NextResponse.json(allTemplates.length > 0 ? allTemplates : UGG_TEMPLATE)
  } catch (error) {
    console.error('AI Email templates error:', error)
    // Fallback to UGG template only
    return NextResponse.json(UGG_TEMPLATE)
  }
}

