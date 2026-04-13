import React from "react";

export interface PinDotsProps {
  total?: number;
  filled?: number;
  activeColor?: string;
  inactiveColor?: string;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: { width: 4, gap: 16 },
  md: { width: 6, gap: 24 },
  lg: { width: 8, gap: 32 },
};

export const PinDots: React.FC<PinDotsProps> = ({
  total = 6,
  filled = 1,
  activeColor = "#6155F5",
  inactiveColor = "rgba(60, 60, 67, 0.18)",
  size = "md",
}) => {
  const { width, gap } = sizeMap[size];
  const totalWidth = total * width * 2 + (total - 1) * gap;

  return (
    <div
      className="flex items-center justify-center relative"
      style={{
        width: `${totalWidth}px`,
        height: `${width * 2}px`,
        gap: `${gap}px`,
      }}
    >
      {Array.from({ length: total }).map((_, index) => (
        <div
          key={index}
          className="rounded-full transition-colors duration-200"
          style={{
            width: `${width * 2}px`,
            height: `${width * 2}px`,
            backgroundColor: index < filled ? activeColor : inactiveColor,
          }}
        />
      ))}
    </div>
  );
};
