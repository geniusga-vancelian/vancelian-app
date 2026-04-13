import React from "react";

export interface CircleButtonProps {
  icon?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  variant?: "default" | "primary" | "secondary";
  className?: string;
}

const sizeClasses = {
  sm: "size-[32px]",
  md: "size-[40px]",
  lg: "size-[48px]",
};

const variantClasses = {
  default: "bg-white",
  primary: "bg-[#6155F5]",
  secondary: "bg-[#f2f2f7]",
};

export const CircleButton: React.FC<CircleButtonProps> = ({
  icon,
  size = "md",
  onClick,
  variant = "default",
  className = "",
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        flex items-center justify-center
        rounded-full
        shadow-[0px_0px_20px_0px_rgba(0,0,0,0.12)]
        transition-transform active:scale-95
        ${className}
      `}
    >
      {icon || <MoreIcon />}
    </button>
  );
};

const MoreIcon: React.FC = () => (
  <div className="relative size-[24px]">
    <svg viewBox="0 0 24 24" fill="none" className="size-full">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M11 3C11 2.44772 11.4477 2 12 2C12.5523 2 13 2.44772 13 3V11H21C21.5523 11 22 11.4477 22 12C22 12.5523 21.5523 13 21 13H13V21C13 21.5523 12.5523 22 12 22C11.4477 22 11 21.5523 11 21V13H3C2.44772 13 2 12.5523 2 12C2 11.4477 2.44772 11 3 11H11V3Z"
        fill="black"
      />
    </svg>
  </div>
);
