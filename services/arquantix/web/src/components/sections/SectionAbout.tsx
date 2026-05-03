/**
 * @deprecated Legacy grid replaced by design-system BlockLeftAndRight; API stable for CMS.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import {
  BlockLeftAndRight,
  TextBlock,
  ImageBlock,
  TextBlockWithChecklist,
} from "@/components/design-system/BlockLeftAndRight";
import { Container } from "@/components/ui/Container";

export interface SectionAboutProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  items?: Array<{
    title: string;
    description: string;
  }>;
  imageUrl?: string;
  content?: string;
  ctaText?: string;
  ctaLink?: string;
}

export function SectionAbout({
  title = "",
  description,
  items = [],
  imageUrl,
  content,
  className,
  ...props
}: SectionAboutProps) {
  const bodyText = [description, content].filter(Boolean).join("\n\n");
  const checklist = items.map((item) => ({
    text: `${item.title}: ${item.description}`,
  }));

  const left =
    checklist.length > 0 ? (
      <TextBlockWithChecklist
        title={title || " "}
        description={bodyText || " "}
        items={checklist}
      />
    ) : (
      <TextBlock
        title={title || " "}
        description={bodyText || description || ""}
      />
    );

  return (
    <section
      className={cn("w-full bg-white py-12 md:py-16", className)}
      {...props}
    >
      <Container>
        <div className="flex w-full min-w-0 justify-center">
          {imageUrl ? (
            <BlockLeftAndRight
              leftContent={left}
              rightContent={
                <ImageBlock src={imageUrl} alt={title || ""} imageStyle="cover" />
              }
            />
          ) : (
            <div className="w-full min-w-0 py-6">{left}</div>
          )}
        </div>
      </Container>
    </section>
  );
}
