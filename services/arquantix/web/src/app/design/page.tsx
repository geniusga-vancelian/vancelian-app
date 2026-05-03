import type { Metadata } from "next";
import { cn } from "@/lib/utils";
import { DesignSystemShowcase } from "@/components/design-system/DesignSystemShowcase";
import { figmaDsPageCanvasBgClassName } from "@/components/design-system/extracted/tokens/surfaces";

export const metadata: Metadata = {
  title: "Design system — Arquantix",
  description:
    "Modules marketing web (Figma) : blocs, galerie, FAQ, footer, page projets.",
};

export default function DesignPage() {
  return (
    <div className={cn("min-h-screen", figmaDsPageCanvasBgClassName)}>
      <header className="border-b bg-white px-6 py-5">
        <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
          Design system (web)
        </h1>
        <p className="mt-1 text-sm text-neutral-600">
          Modules issus des extractions Figma (usage interne). Référence courte
          dans{" "}
          <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs">
            src/components/design-system/DESIGN_SYSTEM.md
          </code>
          .
        </p>
      </header>
      <DesignSystemShowcase />
    </div>
  );
}
