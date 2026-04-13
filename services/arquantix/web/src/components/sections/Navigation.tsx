'use client'

import * as React from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/ui/Logo";
import type { MenuItem } from "@/lib/menu/getPrimaryMenu";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";

export interface NavigationProps extends React.HTMLAttributes<HTMLElement> {
  transparent?: boolean;
  menuItems?: MenuItem[];
  themeColor?: 'dark' | 'light';
}

export function Navigation({ transparent = true, className, menuItems: propMenuItems, themeColor = 'dark', ...props }: NavigationProps) {
  const pathname = usePathname() ?? ''
  
  // Fallback menu items if no menu from DB
  const fallbackMenuItems: MenuItem[] = [
    { id: 'fallback-home', label: 'Home', urlPath: '/', order: 0, type: 'LINK' },
  ];
  
  const menuItems = propMenuItems && propMenuItems.length > 0 ? propMenuItems : fallbackMenuItems;

  // Determine colors based on theme
  const isLight = themeColor === 'light'

  // Separate links and buttons
  const linkItems = menuItems.filter(item => {
    const itemType = item.type || 'LINK' // Default to LINK if type not set
    return itemType === 'LINK'
  })
  const buttonItems = menuItems.filter(item => {
    const itemType = item.type || 'LINK'
    return itemType === 'BUTTON'
  })
  
  // Debug: log button items (remove in production)
  if (typeof window !== 'undefined' && buttonItems.length > 0) {
    console.log('Button items found:', buttonItems.map(item => ({ id: item.id, label: item.label, type: item.type })))
  }

  // Check if a menu item is active based on current pathname
  const isActive = (item: MenuItem) => {
    if (item.urlPath === '/') {
      return pathname === '/'
    }
    return pathname === item.urlPath || pathname.startsWith(item.urlPath + '/')
  }

  // Get button style classes
  const getButtonClasses = (item: MenuItem) => {
    const baseClasses = "px-8 py-3 rounded-full text-[10px] font-medium transition-opacity tracking-wider uppercase"
    const style = item.buttonStyle || 'primary'
    
    switch (style) {
      case 'primary':
        return `${baseClasses} bg-[#C6A47C] hover:opacity-90 text-white`
      case 'secondary':
        return `${baseClasses} bg-gray-600 hover:bg-gray-700 text-white`
      case 'outline':
        return `${baseClasses} border-2 ${isLight ? 'border-black text-black hover:bg-black hover:text-white' : 'border-white text-white hover:bg-white hover:text-black'}`
      default:
        return `${baseClasses} bg-[#C6A47C] hover:opacity-90 text-white`
    }
  }
  const textColor = isLight ? 'text-black' : 'text-white'
  const borderColor = isLight ? 'border-black' : 'border-white'
  const logoColor = isLight ? 'black' : 'white'
  const backgroundColor = isLight ? 'bg-white/20' : 'bg-black/20'

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 w-full",
        transparent && "backdrop-blur-[35px]",
        transparent && backgroundColor,
        className
      )}
      {...props}
    >
      <div className="mx-auto max-w-[1280px] w-full px-16">
        <div className="flex items-center h-20 md:h-24">
          {/* Logo - Left */}
          <div className="flex-shrink-0">
            <Logo className="h-16 w-auto md:h-20" color={logoColor} />
          </div>

          {/* Menu Items (Links) - Centered */}
          <div className="hidden md:flex items-center justify-center gap-10 flex-1">
            {linkItems.map((item) => {
              const active = isActive(item)
              return (
                <a
                  key={item.id}
                  href={item.urlPath}
                  className={cn(
                    "text-[10px] uppercase tracking-wider transition-colors hover:text-[#C6A47C]",
                    textColor,
                    "px-0 py-1.5 border-b",
                    active ? borderColor : "border-transparent"
                  )}
                >
                  {item.label}
                </a>
              )
            })}
          </div>

          {/* Language Switcher & Buttons - Right */}
          <div className="flex-shrink-0 ml-auto flex items-center gap-4">
            <LanguageSwitcher themeColor={themeColor} />
            {buttonItems.map((item) => {
              const handleClick = (e: React.MouseEvent) => {
                if (item.buttonAction && typeof window !== 'undefined' && (window as any)[item.buttonAction!]) {
                  e.preventDefault()
                  ;(window as any)[item.buttonAction!]()
                }
                // If externalUrl is set, the link will handle navigation
              }
              
              const buttonContent = (
                <button
                  key={item.id}
                  onClick={handleClick}
                  className={getButtonClasses(item)}
                  style={{ fontFamily: '"Avenir Next", Avenir, sans-serif' }}
                >
                  {item.label}
                </button>
              )

              // If externalUrl is provided, wrap in anchor
              if (item.externalUrl) {
                return (
                  <a
                    key={item.id}
                    href={item.externalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="no-underline"
                  >
                    {buttonContent}
                  </a>
                )
              }

              return buttonContent
            })}
          </div>

          {/* Mobile Menu Button */}
          <button
            className={cn("md:hidden p-2 ml-auto", textColor)}
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </nav>
  );
}
