import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'cash_data.dart';

/// Transaction status as understood by the UI layer.
enum TransactionDisplayStatus {
  completed,
  pending,
  failed,
  unknown,
}

/// Presentation model for a transaction tile in the Latest Transactions widget.
class TransactionUiModel {
  final String id;
  final String title;
  final String subtitle;
  final String formattedAmount;
  final String dateLabel;

  /// Full French date for the All Transactions list (e.g. "17 mars 2026 • 14:37").
  final String fullDateTime;

  final IconData icon;
  final Color iconBackground;
  final bool isPositive;
  final TransactionDisplayStatus displayStatus;
  final Color amountColor;

  /// Non-null when the transaction is a crypto exchange (buy/sell).
  final String? cryptoTicker;

  /// True when it is an exchange_buy (EUR → crypto), false for exchange_sell.
  final bool isExchangeBuy;

  /// Raw narrative / exchange detail line (e.g. "Buy 0.001 BTC @ 60000").
  final String? exchangeDetail;

  const TransactionUiModel({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.formattedAmount,
    required this.dateLabel,
    required this.fullDateTime,
    required this.icon,
    required this.iconBackground,
    required this.isPositive,
    required this.displayStatus,
    required this.amountColor,
    this.cryptoTicker,
    this.isExchangeBuy = false,
    this.exchangeDetail,
  });

  bool get isExchange => cryptoTicker != null;

  static const Color _creditGreen = Color(0xFF059669);
  static const Color _debitDark = Color(0xFF374151);
  static const Color _pendingAmber = Color(0xFFF59E0B);
  static const Color _failedRed = Color(0xFFDC2626);

  static List<TransactionUiModel> fromCashTransactions(
    List<CashTransaction> transactions, {
    String currencySymbol = '€',
  }) {
    return transactions
        .map((tx) => _mapTransaction(tx, currencySymbol: currencySymbol))
        .toList();
  }

  static TransactionUiModel _mapTransaction(
    CashTransaction tx, {
    String currencySymbol = '€',
  }) {
    final isCredit = tx.direction == 'credit';
    final status = _parseStatus(tx.status);
    final kind = tx.transactionKind;
    final isBuy = kind == 'exchange_buy';
    final isSell = kind == 'exchange_sell';
    final isExchange = isBuy || isSell;

    String? cryptoTicker;
    String? exchangeDetail;
    String title = _resolveTitle(tx, status);
    String subtitle = _resolveSubtitle(tx, status);

    if (isExchange) {
      cryptoTicker = _extractCryptoTicker(tx.narrative ?? subtitle);
      if (cryptoTicker != null) {
        exchangeDetail = subtitle;
        title = isBuy ? 'EUR → $cryptoTicker' : '$cryptoTicker → EUR';
        subtitle = _formatDateLabel(tx.createdAt);
      }
    }

    return TransactionUiModel(
      id: tx.id,
      title: title,
      subtitle: subtitle,
      formattedAmount: _formatAmount(tx.amount, currencySymbol, isCredit),
      dateLabel: _formatDateLabel(tx.createdAt),
      fullDateTime: _formatFullDateTime(tx.createdAt),
      icon: _resolveIcon(tx.type, status, kind: kind),
      iconBackground: _resolveIconColor(tx.type, isCredit, status, kind: kind),
      isPositive: isCredit,
      displayStatus: status,
      amountColor: _resolveAmountColor(isCredit, status),
      cryptoTicker: cryptoTicker,
      isExchangeBuy: isBuy,
      exchangeDetail: exchangeDetail,
    );
  }

  /// Extracts the crypto ticker from a string like "Buy 0.001 BTC @ 60000..."
  static String? _extractCryptoTicker(String text) {
    final parts = text.split(' ');
    if (parts.length >= 3) {
      final candidate = parts[2].toUpperCase();
      if (candidate.length >= 2 && candidate.length <= 6 &&
          RegExp(r'^[A-Z0-9]+$').hasMatch(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  static TransactionDisplayStatus _parseStatus(String raw) {
    switch (raw) {
      case 'completed':
        return TransactionDisplayStatus.completed;
      case 'pending':
      case 'processing':
        return TransactionDisplayStatus.pending;
      case 'failed':
      case 'reversed':
        return TransactionDisplayStatus.failed;
      default:
        return TransactionDisplayStatus.unknown;
    }
  }

  static Color _resolveAmountColor(bool isCredit, TransactionDisplayStatus status) {
    if (status == TransactionDisplayStatus.failed) return _failedRed;
    if (status == TransactionDisplayStatus.pending) return _pendingAmber;
    return isCredit ? _creditGreen : _debitDark;
  }

  static const _kindTitleMap = <String, String>{
    'bank_transfer_in': 'Virement entrant',
    'bank_transfer_out': 'Virement sortant',
    'internal_transfer': 'Transfert interne',
    'exchange_buy': 'Achat',
    'exchange_sell': 'Vente',
  };

  static const _typeTitleMap = <String, String>{
    'deposit': 'Virement entrant',
    'withdrawal': 'Retrait',
    'transfer_internal': 'Transfert interne',
  };

  static String _resolveTitle(CashTransaction tx, TransactionDisplayStatus status) {
    final base = _kindTitleMap[tx.transactionKind]
        ?? _typeTitleMap[tx.type]
        ?? _humanize(tx.type);
    if (status == TransactionDisplayStatus.pending) return '$base (en cours)';
    if (status == TransactionDisplayStatus.failed) return '$base (echoue)';
    return base;
  }

  static String _humanize(String raw) {
    final s = raw.replaceAll('_', ' ');
    if (s.isEmpty) return s;
    return '${s[0].toUpperCase()}${s.substring(1)}';
  }

  static String _resolveSubtitle(CashTransaction tx, TransactionDisplayStatus status) {
    if (tx.remitterName != null && tx.remitterName!.isNotEmpty) {
      return tx.remitterName!;
    }
    if (tx.narrative != null && tx.narrative!.isNotEmpty) {
      return tx.narrative!;
    }
    return 'Compte Euro';
  }

  static String _formatAmount(double amount, String symbol, bool isCredit) {
    final formatter = NumberFormat('#,##0.00', 'fr_FR');
    final sign = isCredit ? '+' : '-';
    return '$sign${formatter.format(amount)} $symbol';
  }

  static IconData _resolveIcon(String type, TransactionDisplayStatus status, {String? kind}) {
    if (status == TransactionDisplayStatus.pending) return Icons.schedule_rounded;
    if (status == TransactionDisplayStatus.failed) return Icons.error_outline_rounded;

    if (kind != null) {
      switch (kind) {
        case 'bank_transfer_in':
          return Icons.account_balance_rounded;
        case 'bank_transfer_out':
          return Icons.outbox_rounded;
        case 'internal_transfer':
          return Icons.swap_horiz_rounded;
        case 'exchange_buy':
          return Icons.shopping_cart_rounded;
        case 'exchange_sell':
          return Icons.sell_rounded;
      }
    }

    switch (type) {
      case 'deposit':
        return Icons.account_balance_rounded;
      case 'withdrawal':
        return Icons.outbox_rounded;
      case 'transfer_internal':
        return Icons.swap_horiz_rounded;
      default:
        return Icons.receipt_long_rounded;
    }
  }

  static Color _resolveIconColor(String type, bool isCredit, TransactionDisplayStatus status, {String? kind}) {
    if (status == TransactionDisplayStatus.pending) return _pendingAmber;
    if (status == TransactionDisplayStatus.failed) return _failedRed;

    if (kind != null) {
      switch (kind) {
        case 'bank_transfer_in':
          return const Color(0xFF3B82F6);
        case 'bank_transfer_out':
          return const Color(0xFF0EA5E9);
        case 'internal_transfer':
          return const Color(0xFF8B5CF6);
        case 'exchange_buy':
          return const Color(0xFF22C55E);
        case 'exchange_sell':
          return const Color(0xFFF97316);
      }
    }

    switch (type) {
      case 'deposit':
        return const Color(0xFF3B82F6);
      case 'withdrawal':
        return const Color(0xFF0EA5E9);
      case 'transfer_internal':
        return const Color(0xFF8B5CF6);
      default:
        return isCredit ? const Color(0xFF22C55E) : const Color(0xFF64748B);
    }
  }

  static const _frenchMonths = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ];

  /// Full French date for TransactionListScreen grouping: "17 mars 2026 • 14:37".
  static String _formatFullDateTime(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final hh = dt.hour.toString().padLeft(2, '0');
      final mm = dt.minute.toString().padLeft(2, '0');
      return '${dt.day} ${_frenchMonths[dt.month - 1]} ${dt.year} • $hh:$mm';
    } catch (_) {
      return '';
    }
  }

  static String _formatDateLabel(String iso) {
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final txDay = DateTime(dt.year, dt.month, dt.day);
      final diff = today.difference(txDay).inDays;

      if (diff == 0) return "Aujourd'hui";
      if (diff == 1) return 'Hier';
      if (diff < 7) return 'Il y a $diff jours';
      return DateFormat('dd/MM/yyyy').format(dt);
    } catch (_) {
      return '';
    }
  }
}
