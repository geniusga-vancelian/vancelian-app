-- Reset financier ciblé gaelitier@gmail.com
-- Conserve : person_crypto_wallets + ledger Privy (person_wallet_*)
-- Supprime : IBAN EUR, transactions plateforme, ordres, positions plateforme

BEGIN;

-- Sauvegardes (hors compte gaelitier@gmail.com)
CREATE TEMP TABLE _keep_ledger_accounts ON COMMIT DROP AS
SELECT *
FROM pe_ledger_accounts
WHERE client_id IS DISTINCT FROM '080358a8-4519-4acf-b5da-25485446c967'::uuid;

CREATE TEMP TABLE _keep_ledger_entries ON COMMIT DROP AS
SELECT le.*
FROM pe_ledger_entries le
WHERE le.account_id IN (SELECT id FROM _keep_ledger_accounts);

CREATE TEMP TABLE _keep_custody_accounts ON COMMIT DROP AS
SELECT *
FROM custody_accounts
WHERE client_id IS DISTINCT FROM '080358a8-4519-4acf-b5da-25485446c967'::uuid;

CREATE TEMP TABLE _keep_custody_balances ON COMMIT DROP AS
SELECT cab.*
FROM custody_account_balances cab
JOIN _keep_custody_accounts k ON k.id = cab.account_id;

-- Purge activité (TRUNCATE contourne les tuples xmax invalides)
TRUNCATE
  client_operation_statement_snapshots,
  custody_webhook_events,
  custody_transactions,
  exchange_orders,
  crypto_positions,
  pe_settlement_instructions,
  pe_trades,
  pe_ledger_entries,
  custody_account_balances,
  custody_accounts,
  pe_ledger_accounts
CASCADE;

-- Restauration des autres clients / comptes settlement
INSERT INTO pe_ledger_accounts SELECT * FROM _keep_ledger_accounts;
INSERT INTO pe_ledger_entries SELECT * FROM _keep_ledger_entries;
INSERT INTO custody_accounts SELECT * FROM _keep_custody_accounts;
INSERT INTO custody_account_balances SELECT * FROM _keep_custody_balances;

COMMIT;
