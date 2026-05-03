/// Données résolues pour afficher le bloc funding (équivalent web `FundingModule` + `_resolved`).
///
/// Les libellés viennent du builder ; les valeurs sont soit métier (auto), soit manuelles.
class VaultFundingUiModel {
  const VaultFundingUiModel({
    required this.moduleTitle,
    required this.showProgressSection,
    required this.showAprRow,
    required this.showTargetRow,
    required this.progress,
    required this.raisedAmount,
    required this.investorsCount,
    required this.progressLabel,
    required this.aprLabel,
    required this.aprValue,
    required this.targetLabel,
    required this.totalFundingAmount,
    this.footnoteMarkdown,
  });

  final String? moduleTitle;

  /// Barre + ligne levée + investisseurs (clé `progress`).
  final bool showProgressSection;

  /// Ligne APR (clé `apr`).
  final bool showAprRow;

  /// Ligne objectif / total (clé `target`).
  final bool showTargetRow;

  /// 0.0–1.0 pour [LinearProgressIndicator].
  final double progress;
  final String raisedAmount;
  final int investorsCount;

  /// Libellé builder pour la zone progression (barre).
  final String progressLabel;

  final String aprLabel;
  final String aprValue;

  final String targetLabel;
  final String totalFundingAmount;

  final String? footnoteMarkdown;
}
