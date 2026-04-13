# SQL Schema — Portfolio Engine

Version: v1.0  
Aligné avec: [PRD_MULTI_ASSET_WALLET.md](./PRD_MULTI_ASSET_WALLET.md)  
Stack: PostgreSQL

---

```sql
-- =========================================================
-- EXTENSIONS
-- =========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================
-- CLIENTS
-- =========================================================
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_ref VARCHAR(100) UNIQUE,
    full_name VARCHAR(255),
    email VARCHAR(255),
    base_currency VARCHAR(20) DEFAULT 'EUR',
    risk_profile VARCHAR(50),
    jurisdiction VARCHAR(50),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- ASSETS
-- =========================================================
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    valuation_source VARCHAR(100),
    liquidity_profile VARCHAR(50),
    risk_profile VARCHAR(50),
    supports_staking BOOLEAN NOT NULL DEFAULT FALSE,
    supports_collateral BOOLEAN NOT NULL DEFAULT FALSE,
    supports_borrowing BOOLEAN NOT NULL DEFAULT FALSE,
    supports_yield BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_metadata ON assets USING GIN(metadata);

-- =========================================================
-- INSTRUMENTS
-- =========================================================
CREATE TABLE instruments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id) ON DELETE RESTRICT,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    instrument_type VARCHAR(50) NOT NULL,
    liquidity_profile VARCHAR(50),
    lockup_period_days INTEGER,
    valuation_method VARCHAR(50),
    yield_source VARCHAR(100),
    provider VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_instruments_asset_id ON instruments(asset_id);
CREATE INDEX idx_instruments_type ON instruments(instrument_type);
CREATE INDEX idx_instruments_metadata ON instruments USING GIN(metadata);

-- =========================================================
-- PORTFOLIOS
-- =========================================================
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    parent_portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    portfolio_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    base_currency VARCHAR(20) NOT NULL DEFAULT 'EUR',
    risk_profile VARCHAR(50),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_portfolios_client_id ON portfolios(client_id);
CREATE INDEX idx_portfolios_type ON portfolios(portfolio_type);

-- =========================================================
-- SLEEVES
-- =========================================================
CREATE TABLE sleeves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sleeve_type VARCHAR(50) NOT NULL,
    allocation_target NUMERIC(12,6),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sleeves_portfolio_id ON sleeves(portfolio_id);

-- =========================================================
-- WALLET CONTAINERS
-- =========================================================
CREATE TABLE wallet_containers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    wallet_type VARCHAR(50) NOT NULL,
    instrument_id UUID REFERENCES instruments(id) ON DELETE SET NULL,
    custody_provider VARCHAR(100),
    blockchain_address VARCHAR(255),
    ledger_account_ref VARCHAR(255),
    jurisdiction VARCHAR(50),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wallet_containers_client_id ON wallet_containers(client_id);
CREATE INDEX idx_wallet_containers_portfolio_id ON wallet_containers(portfolio_id);
CREATE INDEX idx_wallet_containers_type ON wallet_containers(wallet_type);

-- =========================================================
-- STRATEGY DEFINITIONS
-- =========================================================
CREATE TABLE strategy_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    description TEXT,
    parameters_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_definitions_type ON strategy_definitions(strategy_type);

-- =========================================================
-- STRATEGY INSTANCES
-- =========================================================
CREATE TABLE strategy_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE SET NULL,
    strategy_definition_id UUID NOT NULL REFERENCES strategy_definitions(id) ON DELETE RESTRICT,
    name VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    priority INTEGER NOT NULL DEFAULT 100,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_instances_portfolio_id ON strategy_instances(portfolio_id);
CREATE INDEX idx_strategy_instances_sleeve_id ON strategy_instances(sleeve_id);
CREATE INDEX idx_strategy_instances_definition_id ON strategy_instances(strategy_definition_id);
CREATE INDEX idx_strategy_instances_parameters ON strategy_instances USING GIN(parameters);

-- =========================================================
-- REBALANCE POLICIES
-- =========================================================
CREATE TABLE rebalance_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE CASCADE,
    method VARCHAR(50) NOT NULL,
    frequency VARCHAR(50),
    drift_threshold NUMERIC(12,6),
    min_trade_size NUMERIC(30,10),
    transaction_cost_model VARCHAR(50),
    lockup_aware BOOLEAN NOT NULL DEFAULT TRUE,
    cash_flow_priority BOOLEAN NOT NULL DEFAULT TRUE,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (portfolio_id IS NOT NULL AND sleeve_id IS NULL)
        OR
        (portfolio_id IS NULL AND sleeve_id IS NOT NULL)
    )
);

-- =========================================================
-- RISK POLICIES
-- =========================================================
CREATE TABLE risk_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE CASCADE,
    max_ltv NUMERIC(12,6),
    warning_ltv NUMERIC(12,6),
    liquidation_threshold NUMERIC(12,6),
    max_asset_concentration NUMERIC(12,6),
    max_illiquid_exposure NUMERIC(12,6),
    min_cash_buffer NUMERIC(12,6),
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (portfolio_id IS NOT NULL AND sleeve_id IS NULL)
        OR
        (portfolio_id IS NULL AND sleeve_id IS NOT NULL)
    )
);

-- =========================================================
-- POSITION ATOMS
-- =========================================================
CREATE TABLE position_atoms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE SET NULL,
    wallet_id UUID REFERENCES wallet_containers(id) ON DELETE SET NULL,
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE RESTRICT,
    strategy_instance_id UUID REFERENCES strategy_instances(id) ON DELETE SET NULL,
    parent_position_id UUID REFERENCES position_atoms(id) ON DELETE SET NULL,
    position_type VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    quantity NUMERIC(30,10) NOT NULL DEFAULT 0,
    available_quantity NUMERIC(30,10) NOT NULL DEFAULT 0,
    locked_quantity NUMERIC(30,10) NOT NULL DEFAULT 0,
    market_value NUMERIC(30,10),
    cost_basis NUMERIC(30,10),
    average_entry_price NUMERIC(30,10),
    accrued_income NUMERIC(30,10) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(30,10),
    realized_pnl NUMERIC(30,10) NOT NULL DEFAULT 0,
    lockup_status VARCHAR(30),
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_position_atoms_portfolio_id ON position_atoms(portfolio_id);
CREATE INDEX idx_position_atoms_sleeve_id ON position_atoms(sleeve_id);
CREATE INDEX idx_position_atoms_wallet_id ON position_atoms(wallet_id);
CREATE INDEX idx_position_atoms_instrument_id ON position_atoms(instrument_id);
CREATE INDEX idx_position_atoms_strategy_instance_id ON position_atoms(strategy_instance_id);
CREATE INDEX idx_position_atoms_parent_position_id ON position_atoms(parent_position_id);
CREATE INDEX idx_position_atoms_type ON position_atoms(position_type);
CREATE INDEX idx_position_atoms_status ON position_atoms(status);
CREATE INDEX idx_position_atoms_metadata ON position_atoms USING GIN(metadata);

-- =========================================================
-- POSITION RELATIONS
-- =========================================================
CREATE TABLE position_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_position_id UUID NOT NULL REFERENCES position_atoms(id) ON DELETE CASCADE,
    target_position_id UUID NOT NULL REFERENCES position_atoms(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_position_id, target_position_id, relation_type)
);

CREATE INDEX idx_position_relations_source ON position_relations(source_position_id);
CREATE INDEX idx_position_relations_target ON position_relations(target_position_id);
CREATE INDEX idx_position_relations_type ON position_relations(relation_type);

-- =========================================================
-- TARGET ALLOCATIONS
-- =========================================================
CREATE TABLE target_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE CASCADE,
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    target_weight NUMERIC(12,6) NOT NULL,
    min_weight NUMERIC(12,6),
    max_weight NUMERIC(12,6),
    rebalance_priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (portfolio_id IS NOT NULL AND sleeve_id IS NULL)
        OR
        (portfolio_id IS NULL AND sleeve_id IS NOT NULL)
    )
);

CREATE INDEX idx_target_allocations_portfolio_id ON target_allocations(portfolio_id);
CREATE INDEX idx_target_allocations_sleeve_id ON target_allocations(sleeve_id);
CREATE INDEX idx_target_allocations_instrument_id ON target_allocations(instrument_id);

-- =========================================================
-- PRICES / VALUATIONS
-- =========================================================
CREATE TABLE instrument_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    price NUMERIC(30,10) NOT NULL,
    currency VARCHAR(20) NOT NULL DEFAULT 'USD',
    valuation_timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_instrument_prices_instrument_id_ts
    ON instrument_prices(instrument_id, valuation_timestamp DESC);

-- =========================================================
-- PORTFOLIO SNAPSHOTS
-- =========================================================
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    nav NUMERIC(30,10) NOT NULL,
    cash_value NUMERIC(30,10),
    debt_value NUMERIC(30,10),
    gross_exposure NUMERIC(30,10),
    net_exposure NUMERIC(30,10),
    pnl_day NUMERIC(30,10),
    pnl_total NUMERIC(30,10),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(portfolio_id, snapshot_timestamp)
);

CREATE INDEX idx_portfolio_snapshots_portfolio_ts
    ON portfolio_snapshots(portfolio_id, snapshot_timestamp DESC);

-- =========================================================
-- POSITION SNAPSHOTS
-- =========================================================
CREATE TABLE position_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL REFERENCES position_atoms(id) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    quantity NUMERIC(30,10) NOT NULL,
    market_value NUMERIC(30,10),
    accrued_income NUMERIC(30,10),
    unrealized_pnl NUMERIC(30,10),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(position_id, snapshot_timestamp)
);

CREATE INDEX idx_position_snapshots_position_ts
    ON position_snapshots(position_id, snapshot_timestamp DESC);

-- =========================================================
-- EXECUTION INSTRUCTIONS
-- =========================================================
CREATE TABLE execution_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    sleeve_id UUID REFERENCES sleeves(id) ON DELETE SET NULL,
    strategy_instance_id UUID REFERENCES strategy_instances(id) ON DELETE SET NULL,
    instruction_type VARCHAR(50) NOT NULL,
    instrument_id UUID REFERENCES instruments(id) ON DELETE SET NULL,
    source_wallet_id UUID REFERENCES wallet_containers(id) ON DELETE SET NULL,
    destination_wallet_id UUID REFERENCES wallet_containers(id) ON DELETE SET NULL,
    source_position_id UUID REFERENCES position_atoms(id) ON DELETE SET NULL,
    destination_position_id UUID REFERENCES position_atoms(id) ON DELETE SET NULL,
    quantity NUMERIC(30,10),
    amount NUMERIC(30,10),
    currency VARCHAR(20),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    execution_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ
);

CREATE INDEX idx_execution_instructions_portfolio_id ON execution_instructions(portfolio_id);
CREATE INDEX idx_execution_instructions_strategy_id ON execution_instructions(strategy_instance_id);
CREATE INDEX idx_execution_instructions_status ON execution_instructions(status);

-- =========================================================
-- LEDGER TRANSACTIONS
-- =========================================================
CREATE TABLE ledger_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES wallet_containers(id) ON DELETE CASCADE,
    position_id UUID REFERENCES position_atoms(id) ON DELETE SET NULL,
    instruction_id UUID REFERENCES execution_instructions(id) ON DELETE SET NULL,
    transaction_type VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    instrument_id UUID REFERENCES instruments(id) ON DELETE SET NULL,
    quantity NUMERIC(30,10),
    amount NUMERIC(30,10),
    currency VARCHAR(20),
    reference VARCHAR(255),
    transaction_timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ledger_transactions_wallet_id_ts
    ON ledger_transactions(wallet_id, transaction_timestamp DESC);

CREATE INDEX idx_ledger_transactions_position_id_ts
    ON ledger_transactions(position_id, transaction_timestamp DESC);

-- =========================================================
-- EVENTS / AUDIT / DOMAIN EVENTS
-- =========================================================
CREATE TABLE domain_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domain_events_aggregate
    ON domain_events(aggregate_type, aggregate_id, created_at DESC);

CREATE INDEX idx_domain_events_payload ON domain_events USING GIN(payload);
```

---

## Tables (alignement PRD)

| Couche PRD | Table(s) |
|------------|----------|
| Registry | `assets`, `instruments` |
| Ledger | `wallet_containers`, `ledger_transactions` |
| Position | `position_atoms`, `position_relations`, `position_snapshots` |
| Strategy | `strategy_definitions`, `strategy_instances` |
| Portfolio | `portfolios`, `sleeves`, `target_allocations`, `portfolio_snapshots` |
| Rebalance | `rebalance_policies` |
| Risk | `risk_policies` |
| Execution | `execution_instructions` |
| Valuation | `instrument_prices` |
| Audit | `domain_events` |
| Clients | `clients` |
