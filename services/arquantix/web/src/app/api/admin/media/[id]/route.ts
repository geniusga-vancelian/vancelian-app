import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { deleteFile } from '@/lib/storage/storageClient'

/**
 * DELETE /api/admin/media/[id]
 * Delete a media file from R2 and database
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = params

    // Find media record
    const media = await prisma.media.findUnique({
      where: { id },
    })

    if (!media) {
      return NextResponse.json({ error: 'Media not found' }, { status: 404 })
    }

    // Delete from R2
    try {
      await deleteFile(media.key)
    } catch (error) {
      console.error('Error deleting file from R2:', error)
      // Continue to delete database record even if R2 delete fails
    }

    // Delete from database
    await prisma.media.delete({
      where: { id },
    })

    return NextResponse.json({ message: 'Media deleted successfully' })
  } catch (error) {
    console.error('Error deleting media:', error)
    return NextResponse.json(
      { error: 'Failed to delete media' },
      { status: 500 }
    )
  }
}









