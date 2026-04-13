export interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick?: () => void;
  fullWidth?: boolean;
}

export function Button({
  variant = 'primary',
  children,
  onClick,
  fullWidth = false
}: ButtonProps) {
  const baseStyles = "h-[48px] rounded-[9999px] flex items-center justify-center px-[40px]";

  const variantStyles = {
    primary: "bg-[#6155f5] text-white",
    secondary: "bg-white text-black"
  };

  const widthStyle = fullWidth ? "w-full" : "";

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${widthStyle}`}
      onClick={onClick}
    >
      <span className="font-['Inter:Semi_Bold',sans-serif] font-semibold text-[16px] tracking-[-0.31px] leading-[21px]">
        {children}
      </span>
    </button>
  );
}
