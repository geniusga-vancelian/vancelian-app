import * as React from "react";
import { cn } from "@/lib/utils";

export interface CTAButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
}

const CTAButton = React.forwardRef<HTMLButtonElement, CTAButtonProps>(
  (
    { className, variant = "primary", size = "md", icon, children, ...props },
    ref,
  ) => {
    const sizeClasses = {
      sm: "h-10 px-5 py-2 text-[10px]",
      md: "h-[50px] px-6 py-[11px] text-[12px]",
      lg: "h-[60px] px-7 py-[14px] text-[14px]",
    };

    const variantClasses = {
      primary: "bg-black text-white",
      secondary: "border border-black bg-white text-black",
    };

    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          "relative flex shrink-0 items-center justify-center gap-2.5 rounded-[40px] font-ui font-semibold uppercase leading-none tracking-[0.06px] transition-all hover:opacity-90 active:scale-[0.98]",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        <span className="leading-[1.1]">{children}</span>
        {icon ? icon : null}
      </button>
    );
  },
);
CTAButton.displayName = "CTAButton";

export { CTAButton };
