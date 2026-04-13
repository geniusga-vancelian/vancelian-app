/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ARQUANTIX_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
