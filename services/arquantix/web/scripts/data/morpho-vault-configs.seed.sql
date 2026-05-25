-- Sync portal_morpho_vault_configs (local → prod seed)
INSERT INTO "portal_morpho_vault_configs" (
  "id", "vault_address", "chain_id", "integration_mode", "privy_vault_id",
  "label", "description", "curator", "sort_order", "is_published", "updated_at"
) VALUES
  (
    'seed-steakhouse-prime-usdc',
    '0xbeefe94c8ad530842bfe7d8b397938ffc1cb83b2',
    8453, 'privy_earn', 'svbeyhtpw8317205byhv04ns',
    'Steakhouse Prime USDC',
    'Vault Morpho USDC — rendement on-chain via Privy Earn.',
    NULL, 0, true, CURRENT_TIMESTAMP
  ),
  (
    'seed-steakhouse-prime-usdc-v2',
    '0xbeef0e0834849acc03f0089f01f4f1eeb06873c9',
    8453, 'direct_morpho', NULL,
    'Steakhouse Prime USDC',
    'Steakhouse Prime Instant — vault Morpho V2 USDC sur Base (dépôt/retrait direct).',
    'Steakhouse Financial', 1, true, CURRENT_TIMESTAMP
  ),
  (
    'seed-gauntlet-usdc-prime',
    '0x050ce30b927da55177a4914ec73480238bad56f0',
    8453, 'direct_morpho', NULL,
    'Gauntlet USDC Prime',
    'Vault Morpho V2 USDC Gauntlet Prime sur Base — dépôt/retrait direct.',
    'Gauntlet', 2, true, CURRENT_TIMESTAMP
  ),
  (
    'seed-gauntlet-usdc-frontier',
    '0x1deefabee758aabdc29a542b24ca3b75afd56765',
    8453, 'direct_morpho', NULL,
    'Gauntlet USDC Frontier',
    'Vault Morpho V2 USDC Gauntlet Frontier sur Base — rendement plus agressif, dépôt/retrait direct.',
    'Gauntlet', 3, true, CURRENT_TIMESTAMP
  )
ON CONFLICT ("vault_address") DO UPDATE SET
  "chain_id" = EXCLUDED."chain_id",
  "integration_mode" = EXCLUDED."integration_mode",
  "privy_vault_id" = EXCLUDED."privy_vault_id",
  "label" = EXCLUDED."label",
  "description" = EXCLUDED."description",
  "curator" = EXCLUDED."curator",
  "sort_order" = EXCLUDED."sort_order",
  "is_published" = EXCLUDED."is_published",
  "updated_at" = CURRENT_TIMESTAMP;
