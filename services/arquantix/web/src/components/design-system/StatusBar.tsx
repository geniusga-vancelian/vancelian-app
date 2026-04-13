import React from "react";

export interface StatusBarProps {
  time?: string;
  batteryLevel?: number;
  showCellular?: boolean;
  showWifi?: boolean;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  time = "9:41",
  batteryLevel = 100,
  showCellular = true,
  showWifi = true,
}) => {
  const fillWidth = Math.min(21, Math.max(0, (batteryLevel / 100) * 21));

  return (
    <div className="h-[54px] relative w-full" data-name="statusBar">
      <div className="absolute h-[54px] left-0 top-0 w-[98px] flex items-center justify-center">
        <p className="font-semibold leading-[22px] text-[17px] text-black text-center whitespace-nowrap">
          {time}
        </p>
      </div>

      <div className="absolute h-[54px] right-0 top-0 w-[123px] flex items-center justify-end gap-2 pr-4">
        {showCellular && (
          <div className="w-5 h-3">
            <div className="flex gap-0.5 items-end h-full">
              {[1, 2, 3, 4].map((bar) => (
                <div
                  key={bar}
                  className="bg-black flex-1"
                  style={{ height: `${bar * 25}%` }}
                />
              ))}
            </div>
          </div>
        )}

        {showWifi && (
          <div className="w-5 h-4">
            <svg viewBox="0 0 20 16" fill="black" className="size-full" aria-hidden>
              <path d="M10 16c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm7-7c-3.9-3.9-10.1-3.9-14 0l2 2c2.8-2.8 7.2-2.8 10 0l2-2z" />
            </svg>
          </div>
        )}

        <div className="relative w-[27px] h-3 flex items-center">
          <svg width="27" height="12" viewBox="0 0 27 12" aria-hidden>
            <rect
              className="opacity-35"
              fill="black"
              height="12"
              rx="3"
              stroke="black"
              width="24"
            />
            <rect fill="black" height="9" rx="2" width={fillWidth} x="2" y="1.5" />
            <path
              d="M24 5v2c1 0 1.5-.5 1.5-1s-.5-1-1.5-1z"
              fill="black"
              opacity="0.4"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
