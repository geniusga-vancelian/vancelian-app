/// Modèle pour une étape d'un flux transactionnel (conversion, allocation, etc.).
///
/// Compatible JSON/CMS via [fromJson] / [listFromJson].
class TransactionStepItem {
  const TransactionStepItem({
    required this.number,
    required this.title,
    this.primaryText,
    this.primaryWidget,
    this.secondaryText,
    this.approximate = false,
    this.state = TransactionStepState.pending,
    this.iconData,
  });

  final int number;
  final String title;

  /// Texte principal (ex. "0.10 BTC → ≈ 6790.58 USDC"). Ignoré si [primaryWidget] fourni.
  final String? primaryText;

  /// Widget custom à la place de [primaryText] (pour Text.rich, icônes, etc.).
  final dynamic primaryWidget;

  /// Sous-texte explicatif.
  final String? secondaryText;

  /// Si true, les montants sont estimés (≈ affiché côté widget si besoin).
  final bool approximate;

  /// État visuel de l'étape.
  final TransactionStepState state;

  /// Icône optionnelle à la place du numéro.
  final int? iconData;

  /// Désérialisation JSON pour compatibilité CMS.
  static TransactionStepItem? fromJson(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    final title = json['title'] as String?;
    if (title == null || title.isEmpty) return null;
    final number = json['number'] as int? ?? 0;
    final stateStr = json['state'] as String?;
    final state = TransactionStepState.values.firstWhere(
      (s) => s.name == stateStr,
      orElse: () => TransactionStepState.pending,
    );
    return TransactionStepItem(
      number: number,
      title: title,
      primaryText: json['primaryText'] as String?,
      secondaryText: json['secondaryText'] as String?,
      approximate: json['approximate'] == true,
      state: state,
      iconData: json['iconData'] as int?,
    );
  }

  static List<TransactionStepItem> listFromJson(dynamic json) {
    if (json is! List) return [];
    final list = <TransactionStepItem>[];
    for (var i = 0; i < json.length; i++) {
      final item = TransactionStepItem.fromJson(json[i]);
      if (item != null) list.add(item);
    }
    return list;
  }
}

enum TransactionStepState { pending, active, processing, completed }
