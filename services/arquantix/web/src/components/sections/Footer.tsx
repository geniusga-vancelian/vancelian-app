import * as React from "react";
import { cn } from "@/lib/utils";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export interface FooterProps extends React.HTMLAttributes<HTMLElement> {}

const footerLinks = {
  company: [
    { label: "About us", href: "#about" },
    { label: "Projects", href: "#projects" },
    { label: "How it works", href: "#how-it-works" },
  ],
  legal: [
    { label: "Privacy Policy", href: "#privacy" },
    { label: "Terms & Conditions", href: "#terms" },
    { label: "Disclosures", href: "#disclosures" },
  ],
  contact: [
    { label: "Contact", href: "#contact" },
    { label: "Investor Relations", href: "#investors" },
  ],
};

export function Footer({ className, ...props }: FooterProps) {
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
            <p className="text-[#E6E6E6] text-sm leading-relaxed max-w-md">
              Arquantix provides access to fractional ownership of premium real estate 
              assets through a regulated financial structure.
            </p>
          </div>

          {/* Links Columns */}
          <div className="flex flex-col gap-4">
            <h4 className="text-white text-sm uppercase tracking-wider mb-2">
              Company
            </h4>
            {footerLinks.company.map((link, idx) => (
              <a
                key={idx}
                href={link.href}
                className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex flex-col gap-4">
            <h4 className="text-white text-sm uppercase tracking-wider mb-2">
              Legal
            </h4>
            {footerLinks.legal.map((link, idx) => (
              <a
                key={idx}
                href={link.href}
                className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>

        {/* Bottom Section */}
        <div className="border-t border-[#272727] py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[#5F5F5F] text-sm">
            © {new Date().getFullYear()} Arquantix. All rights reserved.
          </p>
          
          <div className="flex items-center gap-6">
            {footerLinks.contact.map((link, idx) => (
              <a
                key={idx}
                href={link.href}
                className="text-[#E6E6E6] text-sm hover:text-[#C6A47C] transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </Container>
    </footer>
  );
}
