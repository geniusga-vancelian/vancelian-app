"use client";

import { useState } from "react";
import ProjetGallery, {
  type Project,
  type TabItem,
} from "./ProjetGallery/ProjetGallery";
import imgImage from "./imports/ExclusiveOffers/0ea7b87e0fb028430d5be3bd5c0071081824fa77.png";
import imgImage1 from "./imports/ExclusiveOffers/b775f6f8ce6fc689a865af4fdc980d94feb91d0c.png";
import imgImage2 from "./imports/ExclusiveOffers/bde784c891e469bd7acf051d0c0d4e4be2f25ed4.png";

const TAB_DEFS: { id: string; label: string }[] = [
  { id: "all", label: "All" },
  { id: "in-progress", label: "In Progress" },
  { id: "upcoming", label: "Upcoming" },
  { id: "delivered", label: "Delivered" },
];

export function ProjetGalleryDemo() {
  const [activeTab, setActiveTab] = useState("in-progress");

  const projects: Project[] = [
    {
      id: "1",
      image: imgImage.src,
      imageStatusLabel: "Funding",
      infoTags: ["Japan", "2 chalets"],
      amount: "€11M",
      title: "Niseko Mori Lodge",
      description:
        "Two luxury ski chalets in Niseko, Asia's Aspen. Home to the world's finest powder snow and Japan's most exclusive alpine destination.",
      fundedPercentage: 26.7,
    },
    {
      id: "2",
      image: imgImage1.src,
      imageStatusLabel: "Coming soon",
      infoTags: ["UAE", "1 Villa"],
      amount: "€11.5M",
      title: "Dubai Al Barari",
      description:
        "Complete renovation of a luxury villa in Al Barari, Dubai's most exclusive green community.",
      fundedPercentage: 26.7,
    },
    {
      id: "3",
      image: imgImage2.src,
      imageStatusLabel: "Funded",
      infoTags: ["Indonesia", "7 villas"],
      amount: "€5.5M",
      title: "Bali Luxury Resort",
      description:
        "Seven luxury mountain villas at 1,000m elevation in Munduk, North Bali's emerging wellness sanctuary.",
      fundedPercentage: 100,
      fundedText: "Funded 100%",
    },
  ];

  const tabs: TabItem[] = TAB_DEFS.map((tab) => ({
    ...tab,
    isActive: tab.id === activeTab,
  }));

  return (
    <ProjetGallery
      sectionLabel="Opportunities"
      title="Exclusive offers."
      subtitle="Institutional-quality real estate investments, now accessible from €1,000."
      tabs={tabs}
      projects={projects}
      viewAllButtonText="Voir toutes les offres"
      viewAllButtonLink="https://arquantix.com"
      onTabChange={(tabId) => setActiveTab(tabId)}
      onProjectClick={() => {}}
    />
  );
}
