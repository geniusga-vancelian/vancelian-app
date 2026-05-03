import clsx from "clsx";
import { twMerge } from "tailwind-merge";

/** Aligné sur `clsx` — import défaut pour éviter un named export `undefined` en bundle RSC (webpack). */
export type ClassValue = Parameters<typeof clsx>[0];

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
