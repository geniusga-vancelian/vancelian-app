import React from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  leftAction?: React.ReactNode;
  rightAction?: React.ReactNode;
  backgroundColor?: string;
  /** Centré (défaut) ou aligné à gauche comme sur l’écran « Choose a code ». */
  titleAlign?: "center" | "left";
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  leftAction,
  rightAction,
  backgroundColor = "#f2f2f7",
  titleAlign = "center",
}) => {
  const isLeft = titleAlign === "left";

  return (
    <div
      className="flex flex-col gap-4 w-full"
      style={{ backgroundColor }}
    >
      {(leftAction || rightAction) && (
        <div className="flex items-center justify-between px-4 h-[60px] w-full">
          <div className="w-[40px] flex justify-start">{leftAction}</div>
          <div className="w-[40px] flex justify-end">{rightAction}</div>
        </div>
      )}

      <div
        className={`flex flex-col gap-2.5 px-4 w-full pb-4 ${
          isLeft ? "items-start" : "items-center"
        }`}
      >
        <h1
          className={`font-bold leading-[34px] text-[28px] text-black tracking-[0.1064px] max-w-full ${
            isLeft ? "text-left" : "text-center whitespace-nowrap"
          }`}
        >
          {title}
        </h1>

        {description && (
          <p
            className={`font-normal leading-[18px] text-[13px] text-[#8e8e93] tracking-[-0.08px] max-w-full ${
              isLeft
                ? "text-left line-clamp-4"
                : "text-center overflow-hidden text-ellipsis"
            }`}
          >
            {description}
          </p>
        )}
      </div>
    </div>
  );
};
