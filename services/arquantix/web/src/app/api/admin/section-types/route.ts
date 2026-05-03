import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { SECTION_TYPES, getSectionTypesEligibleAsCommonModule } from '@/lib/sections/library'
import { getSectionAdminGuide } from '@/lib/sections/sectionTypeAdminGuides'

/**
 * GET /api/admin/section-types
 * Returns the section library metadata (without zod schemas, just metadata)
 *
 * Query `eligibleCommonModule=1` : types autorisés pour créer un module commun (Zone 2).
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const eligibleCommon =
      request.nextUrl.searchParams.get('eligibleCommonModule') === '1' ||
      request.nextUrl.searchParams.get('eligibleCommonModule') === 'true'

    const sourceTypes = eligibleCommon ? getSectionTypesEligibleAsCommonModule() : SECTION_TYPES

    // Exclut les types `deprecated` du catalogue admin (UI « Add section »).
    // Les sections déjà présentes en base avec un type deprecated continuent
    // d'être lues/éditées via leur form spécifique : seule l'UI d'ajout est filtrée.
    const catalogTypes = sourceTypes.filter((type) => !type.deprecated)

    const types = catalogTypes.map((type) => ({
      key: type.key,
      label: type.label,
      category: type.category,
      schemaVersion: type.schemaVersion,
      defaultData: type.defaultData,
      allowedOnTemplates: type.allowedOnTemplates,
      description: type.description,
      adminGuide: getSectionAdminGuide(type.key) || type.description || '',
    }))

    return NextResponse.json({ types })
  } catch (error) {
    console.error('Error fetching section types:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









