"""Ledger wallet Privy utilisateur — dépôts on-chain et soldes (distinct de crypto_positions).

Les routeurs sont importés depuis leurs modules (`webhook_router`, `routes`, `admin_router`)
pour éviter une import circulaire avec ``auth.privy_exchange_routes``.
"""
