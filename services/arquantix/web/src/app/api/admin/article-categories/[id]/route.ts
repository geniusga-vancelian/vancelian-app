import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

// DELETE /api/admin/article-categories/[id] - Delete a category
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const category = await prisma.articleCategory.findUnique({
      where: { id: params.id },
    })

    if (!category) {
      return NextResponse.json({ error: 'Category not found' }, { status: 404 })
    }

    // Check if category is used by any articles
    // Note: Prisma doesn't support array_contains directly for JSON fields
    // We need to fetch all articles and filter in memory
    const allArticles = await prisma.article.findMany({
      select: { id: true, slug: true, categorySlugs: true },
    })

    const articlesWithCategory = allArticles.filter((article) => {
      if (!article.categorySlugs || typeof article.categorySlugs !== 'object') return false
      const slugs = Array.isArray(article.categorySlugs) ? article.categorySlugs : []
      return slugs.includes(category.slug)
    })

    if (articlesWithCategory.length > 0) {
      return NextResponse.json(
        {
          error: 'Cannot delete category',
          message: `This category is used by ${articlesWithCategory.length} article(s). Please remove it from articles first.`,
          articles: articlesWithCategory.map((a) => ({ id: a.id, slug: a.slug })),
        },
        { status: 409 }
      )
    }

    // Delete category (i18n will be cascade deleted)
    await prisma.articleCategory.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ message: 'Category deleted successfully' })
  } catch (error) {
    console.error('Error deleting category:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

