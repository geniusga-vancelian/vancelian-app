import type { Metadata } from "next";
import { DesignSystemShowcase } from "@/components/design-system/DesignSystemShowcase";

export const metadata: Metadata = {
  title: "Design system — Arquantix",
  description:
    "Composants React (PIN, pavé numérique, barres de statut, en-têtes, écran login export Figma).",
};

export default function DesignPage() {
  return (
    <div className="min-h-screen bg-neutral-100">
      <header className="border-b bg-white px-6 py-5">
        <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
          Design system (web)
        </h1>
        <p className="mt-1 text-sm text-neutral-600">
          Composants extraits — usage interne et recette visuelle. Spécifications
          complémentaires dans{" "}
          <code className="text-xs bg-neutral-100 px-1 py-0.5 rounded">
            src/components/design-system/DESIGN_SYSTEM.md
          </code>
          .
        </p>
      </header>
      <DesignSystemShowcase />
    </div>
  );
}
