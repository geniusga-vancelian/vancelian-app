import 'models/transaction_detail.dart';

/// Catégories affichées dans le tag du hero (liste produit restreinte).
enum TransactionHeroCategory {
  exchange,
  /// Virement / mouvement SEPA ou équivalent — sans distinction entrant / sortant.
  transfer,
}

/// Règles d’affichage du détail transaction (tag catégorie, justificatif).
///
/// La liste des transactions « justifiables » est évolutive côté backend ; côté app on
/// commence par les **transferts entrants** (virement SEPA entrant et dépôts créditeurs,
/// y compris crypto).
extension TransactionDetailPresentation on TransactionDetail {
  /// Libellé du tag catégorie : Exchange, transfer, ou repli lisible.
  String get heroCategoryBadgeLabel {
    final cat = heroCategory;
    if (cat != null) {
      switch (cat) {
        case TransactionHeroCategory.exchange:
          return 'Exchange';
        case TransactionHeroCategory.transfer:
          return 'transfer';
      }
    }
    return _fallbackCategoryLabel(transactionType);
  }

  TransactionHeroCategory? get heroCategory {
    final kind = transactionKind?.trim().toLowerCase();
    final type = transactionType.trim().toLowerCase();

    if (kind == 'exchange_buy' || kind == 'exchange_sell' || type == 'exchange') {
      return TransactionHeroCategory.exchange;
    }
    if (kind == 'bank_transfer_in' ||
        kind == 'bank_transfer_out' ||
        (type == 'deposit' && isCredit) ||
        type == 'withdrawal') {
      return TransactionHeroCategory.transfer;
    }
    return null;
  }

  /// `true` si l’action « Justifier » doit être proposée (aligné sur une future liste backend).
  bool get isJustifiable {
    final kind = transactionKind?.trim().toLowerCase();
    if (kind == 'bank_transfer_in') return true;
    if (transactionType.trim().toLowerCase() == 'deposit' && isCredit) return true;
    return false;
  }
}

String _fallbackCategoryLabel(String transactionType) {
  final raw = transactionType.trim().toLowerCase();
  if (raw.isEmpty) return 'Transaction';
  return raw
      .split('_')
      .where((w) => w.isNotEmpty)
      .map(
        (w) =>
            '${w[0].toUpperCase()}${w.length > 1 ? w.substring(1).toLowerCase() : ''}',
      )
      .join(' ');
}
