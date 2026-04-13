import { ArticleBlockType } from '@prisma/client'

/**
 * Calculate reading time in minutes from article blocks
 * Based on average reading speed of 220 words per minute
 */
export function calculateReadingTime(
  blocks: Array<{ type: string; data: unknown }>
): number {
  let totalWords = 0

  for (const block of blocks) {
    switch (block.type as ArticleBlockType) {
      case ArticleBlockType.HEADING:
        const headingText = (block.data as any).text || ''
        totalWords += headingText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.PARAGRAPH:
        const paragraphText = (block.data as any).text || ''
        // Strip markdown syntax (simple regex, safe for common patterns)
        const cleanText = paragraphText
          .replace(/#{1,6}\s+/g, '') // Headers
          .replace(/\*\*([^*]+)\*\*/g, '$1') // Bold
          .replace(/\*([^*]+)\*/g, '$1') // Italic
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Links
          .replace(/`([^`]+)`/g, '$1') // Inline code
          .replace(/```[\s\S]*?```/g, '') // Code blocks
          .replace(/^\s*[-*+]\s+/gm, '') // List markers
          .replace(/^\s*\d+\.\s+/gm, '') // Numbered list markers
        totalWords += cleanText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.QUOTE:
        const quoteText = (block.data as any).text || ''
        totalWords += quoteText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.BULLET_LIST:
        const items = (block.data as any).items || []
        if (Array.isArray(items)) {
          items.forEach((item: string) => {
            if (typeof item === 'string') {
              totalWords += item.split(/\s+/).filter((w: string) => w.length > 0).length
            }
          })
        }
        break

      // IMAGE and VIDEO blocks don't contribute to word count
    }
  }

  // Calculate minutes (220 words per minute average)
  const minutes = Math.ceil(totalWords / 220)
  return Math.max(1, minutes) // Minimum 1 minute
}


