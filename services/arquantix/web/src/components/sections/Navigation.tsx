import * as React from "react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/button";

export interface NavigationProps extends React.HTMLAttributes<HTMLElement> {
  transparent?: boolean;
}

export function Navigation({ transparent = true, className, ...props }: NavigationProps) {
  const menuItems = {
    left: ["Home", "Projets", "À Propos"],
    right: ["Menu 4", "Menu 5", "Menu 6"],
  };

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 w-full",
        transparent && "backdrop-blur-[35px] bg-black/20",
        className
      )}
      {...props}
    >
      <div className="mx-auto max-w-[1280px] w-full px-16">
        <div className="flex items-center justify-between h-20 md:h-24">
          {/* Left Menu */}
          <div className="hidden md:flex items-center gap-10 flex-1">
            {menuItems.left.map((item, idx) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className={cn(
                  "text-[10px] uppercase tracking-wider text-white transition-colors hover:text-[#C6A47C]",
                  "px-0 py-1.5 border-b border-transparent",
                  idx === 0 && "border-b border-white"
                )}
              >
                {item}
              </a>
            ))}
          </div>

          {/* Center Logo */}
          <div className="flex-shrink-0">
            <Logo className="h-16 w-auto md:h-20" />
          </div>

          {/* Right Menu */}
          <div className="hidden md:flex items-center justify-end gap-10 flex-1">
            {menuItems.right.map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace(/\s/g, "-")}`}
                className="text-[10px] uppercase tracking-wider text-white transition-colors hover:text-[#C6A47C] px-0 py-1.5"
              >
                {item}
              </a>
            ))}
            <Button variant="arquantix" size="arquantix" asChild>
              <a href="https://wa.me/6281353009603?text=Hello,%20I'm%20interested%20in%20The%20Heights%20Munduk">
                Call to action
              </a>
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-white p-2"
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
