/**
 * Couche vault : normalisation lecture seule des modules `vault_builder_v1`.
 */
export {
  normalizeDocumentsListModuleContent,
  normalizeVaultBuilderSectionDataRoot,
  normalizeVaultModulesArray,
  normalizeVaultModulesFromSectionData,
  type NormalizeVaultModulesResult,
  type NormalizedVaultModule,
} from '@/lib/vault/normalizeVaultModules'
export {
  hasWebExplicitRenderer,
  isAdminRegisteredVaultModuleType,
  VAULT_MODULE_TYPES_ADMIN,
  VAULT_MODULE_TYPES_WEB_EXPLICIT,
} from '@/lib/vault/vaultModuleRegistry'
