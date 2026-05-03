import * as React from "react";
import { cn } from "@/lib/utils";
import { CTAButton } from "./cta-button";

export interface EmailInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onSubmit"> {
  onSubmit?: (email: string) => void;
  buttonText?: string;
  containerClassName?: string;
}

/**
 * Bloc hero DS : une seule pilule (bord gris léger) — champ email à gauche, CTA primary (`CTAButton`) noir à droite, intégré dans le même contour.
 */
const EmailInput = React.forwardRef<HTMLInputElement, EmailInputProps>(
  (
    {
      className,
      containerClassName,
      onSubmit,
      buttonText = "get in touch",
      placeholder = "Enter your email",
      ...props
    },
    ref,
  ) => {
    const [email, setEmail] = React.useState("");

    const handleSubmit = () => {
      if (onSubmit && email.trim()) {
        onSubmit(email.trim());
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleSubmit();
      }
    };

    return (
      <div
        className={cn(
          "flex h-[50px] w-full max-w-[min(100%,492px)] shrink-0 items-stretch overflow-hidden rounded-[32px] border border-solid border-[rgba(59,63,99,0.2)] bg-white",
          containerClassName,
        )}
      >
        <input
          ref={ref}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn(
            "min-w-0 flex-1 border-none bg-transparent px-6 font-['Avenir:Book',sans-serif] text-[14px] leading-[1.6] text-[#62656e] outline-none placeholder:text-[#62656e]/70",
            className,
          )}
          {...props}
        />
        <CTAButton
          type="button"
          variant="primary"
          size="md"
          onClick={handleSubmit}
          className="min-h-0 w-[35%] min-w-[130px] max-w-[200px] shrink-0 rounded-l-full rounded-r-[32px] border-0 px-4 sm:px-6"
        >
          {buttonText.toUpperCase()}
        </CTAButton>
      </div>
    );
  },
);
EmailInput.displayName = "EmailInput";

export { EmailInput };
