-- Add Ledgity vault integration mode to portal vault configs.
ALTER TYPE "PortalMorphoIntegrationMode" ADD VALUE IF NOT EXISTS 'ledgity_vault';
