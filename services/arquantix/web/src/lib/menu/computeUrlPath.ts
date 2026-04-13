/**
 * Compute URL path for a menu item
 * - If isRoot => "/"
 * - Else if page.slug === "home" => "/"
 * - Else => "/" + page.slug
 */
export function computeMenuItemUrlPath(
  isRoot: boolean,
  pageSlug: string | null | undefined
): string {
  if (isRoot) {
    return '/'
  }
  
  if (!pageSlug) {
    // Invalid state: not root but no page
    return '/'
  }
  
  if (pageSlug === 'home') {
    return '/'
  }
  
  return `/${pageSlug}`
}


