import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export interface FooterProps extends React.HTMLAttributes<HTMLElement> {
  copyright?: string;
  description?: string;
  links?: Array<{
    label: string;
    href: string;
    category?: string;
  }>;
}

export function Footer({ 
  copyright,
  description,
  links = [],
  className, 
  ...props 
}: FooterProps) {
  // Group links by category if provided
  const groupedLinks = links.reduce((acc, link) => {
    const category = link.category || 'other'
    if (!acc[category]) acc[category] = []
    acc[category].push(link)
    return acc
  }, {} as Record<string, Array<{ label: string; href: string }>>)

  const companyLinks = groupedLinks.company || []
  const legalLinks = groupedLinks.legal || []
  const contactLinks = groupedLinks.contact || []
  return (
    <footer
      className={cn("w-full bg-[#0D0D0D] border-t border-[#272727]", className)}
      {...props}
    >
      <Container>
        {/* Top Section */}
        <div className="py-16 md:py-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          {/* Logo & Description */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            <Logo className="h-16 w-auto" />
            {description && (
              <p className="text-[#E6E6E6] text-sm leading-relaxed max-w-md">
                {description}
              </p>
            )}
          </div>

          {/* Links Columns */}
          {companyLinks.length > 0 && (
            <div className="flex flex-col gap-4">
              <h4 className="text-white text-sm uppercase tracking-wider mb-2">
                Company
              </h4>
              {companyLinks.map((link, idx) => (
                <a
                  key={idx}
                  href={link.href}
                  className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          )}

          {legalLinks.length > 0 && (
            <div className="flex flex-col gap-4">
              <h4 className="text-white text-sm uppercase tracking-wider mb-2">
                Legal
              </h4>
              {legalLinks.map((link, idx) => (
                <a
                  key={idx}
                  href={link.href}
                  className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Bottom Section */}
        <div className="border-t border-[#272727] py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[#5F5F5F] text-sm">
            {copyright || `© ${new Date().getFullYear()} Arquantix. All rights reserved.`}
          </p>
          
          {contactLinks.length > 0 && (
            <div className="flex items-center gap-6">
              {contactLinks.map((link, idx) => (
                <a
                  key={idx}
                  href={link.href}
                  className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          )}
        </div>
      </Container>
    </footer>
  );
}
