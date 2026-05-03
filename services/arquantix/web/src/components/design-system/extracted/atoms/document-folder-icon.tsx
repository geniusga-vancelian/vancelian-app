import { useId } from 'react'
import { cn } from '@/lib/utils'

type DocumentFolderIconProps = {
  className?: string
  title?: string
}

/** Icône dossier module liste documents (source Figma `foldr icon.svg`). */
export function DocumentFolderIcon({ className, title }: DocumentFolderIconProps) {
  const rawId = useId()
  const clipId = `document-folder-clip-${rawId.replace(/:/g, '')}`

  return (
    <svg
      viewBox="0 0 27 25"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('h-[25px] w-[27px] shrink-0', className)}
      role={title ? 'img' : 'presentation'}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      <g clipPath={`url(#${clipId})`}>
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M25.4004 8.06678H24.1183V5.58469C24.1183 4.90026 23.5433 4.34365 22.8363 4.34365H14.503C14.353 4.34365 14.2081 4.29277 14.0927 4.20031L10.4247 1.24104H2.96449C2.25744 1.24104 1.68244 1.79765 1.68244 2.48209V6.82574H25.4004V8.06678H1.68244H0.400391V2.48209C0.400391 1.11322 1.55039 0 2.96449 0H10.6568C10.8068 0 10.9517 0.0508828 11.0671 0.14334L14.735 3.10261H22.8363C24.2504 3.10261 25.4004 4.21582 25.4004 5.58469V8.06678Z"
          fill="currentColor"
        />
        <rect y="6" width="27" height="18" rx="2" fill="currentColor" />
      </g>
      <defs>
        <clipPath id={clipId}>
          <rect width="27" height="25" fill="white" />
        </clipPath>
      </defs>
    </svg>
  )
}
