import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { SECTION_TYPES } from '@/lib/sections/library'

/**
 * GET /api/admin/section-types
 * Returns the section library metadata (without zod schemas, just metadata)
 */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Return section types without zod schemas (they're not serializable)
    const types = SECTION_TYPES.map((type) => ({
      key: type.key,
      label: type.label,
      category: type.category,
      schemaVersion: type.schemaVersion,
      defaultData: type.defaultData,
      allowedOnTemplates: type.allowedOnTemplates,
      description: type.description,
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









