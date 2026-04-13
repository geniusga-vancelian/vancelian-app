import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../domain/models/cash_data.dart';

class CashBalanceCard extends StatelessWidget {
  final CashData data;
  const CashBalanceCard({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final account = data.cashAccount;
    final balance = account?.availableBalance ?? 0;
    final currency = account?.currency ?? 'EUR';
    final iban = account?.iban ?? '—';
    final lastTx = data.recentTransactions.isNotEmpty
        ? data.recentTransactions.first
        : null;

    final symbol = account?.currencySymbol ?? _currencySymbol(currency);

    final formatter = NumberFormat.currency(
      locale: 'fr_FR',
      symbol: symbol,
      decimalDigits: 2,
    );

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1A1A2E), Color(0xFF16213E)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Cash Balance',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    currency,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              formatter.format(balance),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 32,
                fontWeight: FontWeight.bold,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'IBAN: $iban',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 12,
                fontFamily: 'monospace',
              ),
            ),
            if (lastTx != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    Icon(
                      lastTx.direction == 'credit'
                          ? Icons.arrow_downward_rounded
                          : Icons.arrow_upward_rounded,
                      color: lastTx.direction == 'credit'
                          ? const Color(0xFF4ADE80)
                          : const Color(0xFFF87171),
                      size: 18,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            lastTx.remitterName != null && lastTx.remitterName!.isNotEmpty
                                ? '${_txLabel(lastTx)} — ${lastTx.remitterName}'
                                : _txLabel(lastTx),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            _formatTxDate(lastTx.createdAt),
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.4),
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      '${lastTx.direction == 'credit' ? '+' : '-'}${formatter.format(lastTx.amount)}',
                      style: TextStyle(
                        color: lastTx.direction == 'credit'
                            ? const Color(0xFF4ADE80)
                            : const Color(0xFFF87171),
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _currencySymbol(String currency) {
    switch (currency.toUpperCase()) {
      case 'EUR':
        return '€';
      case 'USD':
        return '\$';
      case 'GBP':
        return '£';
      default:
        return currency;
    }
  }

  static String _txLabel(CashTransaction tx) {
    final type = tx.type.replaceAll('_', ' ');
    return '${type[0].toUpperCase()}${type.substring(1)}';
  }

  static String _formatTxDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('dd/MM/yyyy HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }
}
