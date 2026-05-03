import clsx from "clsx";
import { twMerge } from "tailwind-merge";

export type ClassValue = Parameters<typeof clsx>[0];

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
