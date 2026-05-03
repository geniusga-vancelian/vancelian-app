import 'exclusive_offer_formatting.dart';
import 'models/offer_project.dart';
import 'models/vault_offer_builder_models.dart';

/// Première occurrence d’un [TagsModule] activé — puces hero (déjà localisées côté CMS).
List<String> parseVaultHeroTags(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return const [];
  final modules = vaultData['modules'];
  if (modules is! List) return const [];
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final type = (m['type'] ?? m['module'])?.toString() ?? '';
    if (type != 'TagsModule') continue;
    final content = m['content'];
    if (content is! Map) continue;
    final c = Map<String, dynamic>.from(content);
    final tagsRaw = c['tags'];
    if (tagsRaw is! List) continue;
    final out = <String>[];
    for (final e in tagsRaw) {
      final s = e?.toString().trim() ?? '';
      if (s.isNotEmpty) out.add(s);
      if (out.length >= 10) break;
    }
    if (out.isNotEmpty) return out;
  }
  return const [];
}

Map<String, dynamic>? _firstFundingModuleContent(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final type = (m['type'] ?? m['module'])?.toString() ?? '';
    if (type != 'FundingModule') continue;
    final content = m['content'];
    if (content is! Map) continue;
    return Map<String, dynamic>.from(content);
  }
  return null;
}

({bool enabled, String label}) _itemCfg(List<dynamic>? items, String key) {
  if (items is! List) return (enabled: true, label: '');
  for (final raw in items) {
    if (raw is! Map) continue;
    final o = Map<String, dynamic>.from(raw);
    if ((o['key']?.toString() ?? '') != key) continue;
    final enabled = o['enabled'] != false;
    final label = (o['label']?.toString() ?? '').trim();
    return (enabled: enabled, label: label);
  }
  return (enabled: true, label: '');
}

String _formatAprForDisplay(double? apy) {
  if (apy == null || !apy.isFinite) return '';
  return formatExclusiveOfferAprPercent(apy);
}

/// Résout l’affichage funding à partir du vault + snapshot lending déjà fusionné dans [project].
VaultFundingUiModel? resolveVaultFundingUi({
  required OfferProject project,
  required Map<String, dynamic>? vaultData,
}) {
  final content = _firstFundingModuleContent(vaultData);
  if (content == null) return null;

  final itemsRaw = content['items'];
  final items = itemsRaw is List ? itemsRaw : null;
  final pCfg = _itemCfg(items, 'progress');
  final aCfg = _itemCfg(items, 'apr');
  final tCfg = _itemCfg(items, 'target');

  if (!pCfg.enabled && !aCfg.enabled && !tCfg.enabled) return null;

  final modeRaw = (content['displayMode'] ?? 'auto_product').toString();
  final manual = modeRaw == 'manual';

  final titleRaw = (content['title'] ?? '').toString().trim();
  final footRaw = (content['footnote'] ?? '').toString().trim();

  double progress01 = project.progressRatio;
  var raisedLine = '${project.raisedFormatted} ${project.lendingAsset ?? 'EUR'}';
  var totalLine = '${project.targetFormatted} ${project.lendingAsset ?? 'EUR'}';
  var aprLine = _formatAprForDisplay(project.apy);
  final investors = project.investorsCount ?? 0;

  if (manual) {
    final man = content['manual'];
    if (man is! Map) return null;
    final mm = Map<String, dynamic>.from(man);
    final pctRaw = mm['progressPct'];
    double pct = 0;
    if (pctRaw is num) {
      pct = pctRaw.toDouble();
    } else if (pctRaw is String) {
      pct = double.tryParse(pctRaw.trim()) ?? 0;
    }
    pct = pct.clamp(0, 100);
    progress01 = (pct / 100.0).clamp(0.0, 1.0);
    aprLine = (mm['rateDisplay'] ?? '').toString().trim();
    totalLine = (mm['totalDisplay'] ?? '').toString().trim();
    // Pas de montant « levé » séparé en JSON manuel : afficher le % comme métrique principale de la 1ʳᵉ ligne.
    raisedLine = pCfg.enabled ? '${pct.round()}%' : '';
  } else {
    if (pCfg.enabled && !project.hasLendingData) return null;
    if (tCfg.enabled && (project.target == null || project.target! <= 0)) return null;
    if (aCfg.enabled && (project.apy == null || !project.apy!.isFinite)) return null;
  }

  final showProgress = pCfg.enabled;
  final showApr = aCfg.enabled && aprLine.isNotEmpty;
  final showTarget = tCfg.enabled && totalLine.isNotEmpty;

  if (!showProgress && !showApr && !showTarget) return null;

  if (showProgress && raisedLine.isEmpty && !manual) {
    raisedLine = '${project.raisedFormatted} ${project.lendingAsset ?? 'EUR'}';
  }

  return VaultFundingUiModel(
    moduleTitle: titleRaw.isEmpty ? null : titleRaw,
    showProgressSection: showProgress,
    showAprRow: showApr,
    showTargetRow: showTarget,
    progress: progress01,
    raisedAmount: raisedLine,
    investorsCount: investors,
    progressLabel: pCfg.label,
    aprLabel: aCfg.label,
    aprValue: aprLine,
    targetLabel: tCfg.label,
    totalFundingAmount: totalLine,
    footnoteMarkdown: footRaw.isEmpty ? null : footRaw,
  );
}
