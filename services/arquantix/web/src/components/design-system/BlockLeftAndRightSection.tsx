import {
  BlockLeftAndRight,
  TextBlock,
  ImageBlock,
  TextBlockWithChecklist,
} from "./BlockLeftAndRight";
import { DecorativeOverlay } from "./DecorativeOverlay";
import imgImage from "./imports/Arguments/e097313f401adc12e56cffe475ec7041bd5a9a1d.png";
import imgImage1 from "./imports/Arguments/5f529eb7a115a2504e05f35c5f648d8be648e2d5.png";

export function BlockLeftAndRightSection() {
  return (
    <div className="flex w-full flex-col items-center gap-16">
      <BlockLeftAndRight
        leftContent={
          <TextBlock
            title="Transparency is not optional."
            description="All investments involve risk. Arquantix is committed to providing clear, factual and structured information to enable informed investment decisions."
            subdescription="Full documentation, disclosures and performance reporting available anytime on the platform."
          />
        }
        rightContent={
          <ImageBlock
            src={imgImage.src}
            alt="Transparency"
            overlay={<DecorativeOverlay variant="right-bottom" />}
          />
        }
      />

      <BlockLeftAndRight
        leftContent={
          <ImageBlock
            src={imgImage1.src}
            alt="Quick registration"
            imageStyle="cover"
            overlay={<DecorativeOverlay variant="left-top" />}
          />
        }
        rightContent={
          <TextBlockWithChecklist
            title={["Quick registration,", "minimal needed."]}
            description="Access opportunities in a few clicks. Our process is designed for discerning investors who value their time."
            items={[
              { text: "Identity verification in under 5 minutes" },
              { text: "No prohibitive minimum investment" },
              { text: "Personal dashboard from day one" },
            ]}
          />
        }
      />
    </div>
  );
}
