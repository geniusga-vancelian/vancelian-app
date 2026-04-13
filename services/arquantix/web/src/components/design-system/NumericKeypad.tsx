import React from "react";

const keyBaseClass =
  "rounded-full size-[85px] flex items-center justify-center active:scale-[0.97] transition-all " +
  "shadow-[0_2px_14px_rgba(0,0,0,0.07)]";

export interface NumericKeypadProps {
  onNumberPress?: (number: number) => void;
  onBackspace?: () => void;
  selectedNumber?: number | null;
  showBackspace?: boolean;
  backspaceIcon?: React.ReactNode;
  /** Contenu de la case bas-gauche (ex. Face ID), même gabarit que les touches chiffres. */
  bottomLeftSlot?: React.ReactNode;
  onBottomLeftPress?: () => void;
}

export const NumericKeypad: React.FC<NumericKeypadProps> = ({
  onNumberPress,
  onBackspace,
  selectedNumber = null,
  showBackspace = true,
  backspaceIcon,
  bottomLeftSlot,
  onBottomLeftPress,
}) => {
  const numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, null, 0, "backspace"] as const;

  const handlePress = (value: number | null | "backspace") => {
    if (value === "backspace" && onBackspace) {
      onBackspace();
    } else if (typeof value === "number" && onNumberPress) {
      onNumberPress(value);
    }
  };

  return (
    <div className="grid grid-cols-3 gap-x-5 gap-y-4 px-6 pt-2 pb-8 w-full max-w-[375px]">
      {numbers.map((num, index) => {
        if (num === null) {
          if (bottomLeftSlot) {
            if (onBottomLeftPress) {
              return (
                <button
                  type="button"
                  key={index}
                  onClick={onBottomLeftPress}
                  className={`${keyBaseClass} bg-white text-black`}
                  aria-label="Face ID"
                >
                  {bottomLeftSlot}
                </button>
              );
            }
            return (
              <div
                key={index}
                className={`${keyBaseClass} bg-white text-black`}
                aria-hidden
              >
                {bottomLeftSlot}
              </div>
            );
          }
          return <div key={index} />;
        }

        if (num === "backspace") {
          return showBackspace ? (
            <button
              type="button"
              key={index}
              onClick={() => handlePress("backspace")}
              className={`${keyBaseClass} bg-white`}
            >
              {backspaceIcon || <BackspaceIcon />}
            </button>
          ) : (
            <div key={index} />
          );
        }

        const isSelected = selectedNumber === num;

        return (
          <button
            type="button"
            key={index}
            onClick={() => handlePress(num)}
            className={`${keyBaseClass} font-normal text-[36px] text-black ${
              isSelected
                ? "bg-[#EDE9FE] ring-2 ring-[#6155F5] shadow-[0_4px_16px_rgba(97,85,245,0.18)]"
                : "bg-white"
            }`}
          >
            {num}
          </button>
        );
      })}
    </div>
  );
};

const BackspaceIcon: React.FC = () => (
  <svg width="31" height="25" viewBox="0 0 31 25" fill="none" aria-hidden>
    <path
      d="M28.934 0H10.7c-.8 0-1.5.4-2 1L.3 11.3c-.4.5-.4 1.2 0 1.7l8.4 10.3c.5.6 1.2 1 2 1h18.2c1.2 0 2.1-1 2.1-2.1V2.1C31 1 30 0 28.9 0zm-3.5 17.9c.4.4.4 1 0 1.4-.2.2-.5.3-.7.3-.3 0-.5-.1-.7-.3l-4.5-4.5-4.5 4.5c-.2.2-.5.3-.7.3-.3 0-.5-.1-.7-.3-.4-.4-.4-1 0-1.4l4.5-4.5-4.5-4.5c-.4-.4-.4-1 0-1.4.4-.4 1-.4 1.4 0l4.5 4.5 4.5-4.5c.4-.4 1-.4 1.4 0 .4.4.4 1 0 1.4l-4.5 4.5 4.5 4.5z"
      fill="black"
    />
  </svg>
);
