import 'models/catalog_product.dart';
import 'models/offer_project.dart';

/// Mappe les réponses catalogue (Product Registry) vers [OfferProject] pour réutiliser l’UI existante.
class CatalogOfferMapper {
  CatalogOfferMapper._();

  static OfferProject fromListItem(CatalogListItem item) {
    final lending = _lendingFromSnapshot(item.engine.snapshot);
    final id = (item.legacyProjectId != null && item.legacyProjectId!.trim().isNotEmpty)
        ? item.legacyProjectId!.trim()
        : item.id;
    return OfferProject(
      id: id,
      imageUrl: item.coverUrl ?? '',
      title: item.title,
      category: _displayCategory(item.categorySlug),
      shortDescription: item.subtitle,
      description: null,
      descriptionLinks: null,
      descriptionModuleTitle: null,
      howItWorks: null,
      keyInformation: null,
      teaserVideoUrl: null,
      promoVideoUrls: const [],
      hasGallery: false,
      competitiveAdvantages: null,
      faq: null,
      bottomPageMarkdown: null,
      apy: lending.apy,
      raised: lending.raised,
      target: lending.target,
      progress: lending.progress,
      investorsCount: lending.investorsCount,
      durationMonths: lending.durationMonths,
      lendingAsset: lending.lendingAsset,
      lendingStatus: lending.lendingStatus,
      isInvestable: lending.isInvestable,
      lendingProductId: lending.lendingProductId,
      entryAssetDefault: lending.entryAssetDefault,
      entryAssetsAllowed: lending.entryAssetsAllowed,
      catalogSlug: item.slug,
      packagedProductId: item.id,
    );
  }

  /// Fusionne le détail catalogue (vault + snapshot moteur) avec un [OfferProject] déjà affiché (navigation).
  static OfferProject mergeWithDetail(OfferProject base, CatalogProductDetail detail) {
    final snap = detail.engine.snapshot;
    final lending = _lendingFromSnapshot(snap);
    final cms = _parseVaultModules(detail.vaultData);
    final pres = detail.presentation;
    final packaged = detail.packagedProduct;
    final legacy = packaged.legacyProjectId?.trim();
    final id = (legacy != null && legacy.isNotEmpty) ? legacy : base.id;

    final promoFromVault = _parsePromoVideoUrlsFromVault(detail.vaultData);
    final mergedPromo = promoFromVault.isNotEmpty
        ? promoFromVault
        : (base.promoVideoUrls.isNotEmpty
            ? base.promoVideoUrls
            : (base.teaserVideoUrl != null && base.teaserVideoUrl!.trim().isNotEmpty
                ? <String>[base.teaserVideoUrl!.trim()]
                : <String>[]));

    return OfferProject(
      id: id,
      imageUrl: (pres.coverUrl != null && pres.coverUrl!.trim().isNotEmpty)
          ? pres.coverUrl!.trim()
          : base.imageUrl,
      title: pres.title.trim().isNotEmpty ? pres.title : base.title,
      category: _displayCategory(packaged.categorySlug ?? base.category),
      shortDescription:
          (pres.subtitle != null && pres.subtitle!.trim().isNotEmpty) ? pres.subtitle : base.shortDescription,
      description: cms.description ?? base.description,
      descriptionLinks: cms.descriptionLinks ?? base.descriptionLinks,
      descriptionModuleTitle: cms.descriptionModuleTitle ?? base.descriptionModuleTitle,
      howItWorks: cms.howItWorks ?? base.howItWorks,
      keyInformation: cms.keyInformation ?? base.keyInformation,
      teaserVideoUrl: mergedPromo.isNotEmpty ? mergedPromo.first : base.teaserVideoUrl,
      promoVideoUrls: mergedPromo,
      hasGallery: base.hasGallery,
      competitiveAdvantages: cms.competitiveAdvantages ?? base.competitiveAdvantages,
      faq: cms.faq ?? base.faq,
      bottomPageMarkdown: cms.bottomPageMarkdown ?? base.bottomPageMarkdown,
      apy: lending.apy ?? base.apy,
      raised: lending.raised ?? base.raised,
      target: lending.target ?? base.target,
      progress: lending.progress ?? base.progress,
      investorsCount: lending.investorsCount ?? base.investorsCount,
      durationMonths: lending.durationMonths ?? base.durationMonths,
      lendingAsset: lending.lendingAsset ?? base.lendingAsset,
      lendingStatus: lending.lendingStatus ?? base.lendingStatus,
      isInvestable: lending.hasLendingFields ? lending.isInvestable : base.isInvestable,
      lendingProductId: lending.lendingProductId ?? base.lendingProductId,
      entryAssetDefault: lending.entryAssetDefault ?? base.entryAssetDefault,
      entryAssetsAllowed: lending.entryAssetsAllowed ?? base.entryAssetsAllowed,
      catalogSlug: packaged.slug.trim().isNotEmpty ? packaged.slug : base.catalogSlug,
      packagedProductId: packaged.id.trim().isNotEmpty ? packaged.id : base.packagedProductId,
    );
  }
}

class _LendingFromSnapshot {
  const _LendingFromSnapshot({
    this.apy,
    this.raised,
    this.target,
    this.progress,
    this.investorsCount,
    this.durationMonths,
    this.lendingAsset,
    this.lendingStatus,
    this.isInvestable = false,
    this.lendingProductId,
    this.entryAssetDefault,
    this.entryAssetsAllowed,
    this.hasLendingFields = false,
  });

  final double? apy;
  final double? raised;
  final double? target;
  final double? progress;
  final int? investorsCount;
  final int? durationMonths;
  final String? lendingAsset;
  final String? lendingStatus;
  final bool isInvestable;
  final String? lendingProductId;
  final String? entryAssetDefault;
  final List<String>? entryAssetsAllowed;
  final bool hasLendingFields;
}

_LendingFromSnapshot _lendingFromSnapshot(Map<String, dynamic>? snap) {
  if (snap == null || snap.isEmpty) {
    return const _LendingFromSnapshot();
  }
  double? numVal(Object? k) {
    if (k == null) return null;
    if (k is num) return k.toDouble();
    if (k is String) return double.tryParse(k.trim());
    return null;
  }

  final apy = numVal(snap['supply_apr']);
  final raised = numVal(snap['current_raised']);
  final target = numVal(snap['target_size']);
  final progress = numVal(snap['progress_pct']);
  final investors = snap['investors_count'];
  final investorsCount = investors is int
      ? investors
      : investors is num
          ? investors.toInt()
          : investors is String
              ? int.tryParse(investors.trim())
              : null;

  final status = snap['status'] as String?;
  final isInvestable = status == 'fundraising';

  final lendingProductId = snap['product_id']?.toString();

  final asset = snap['asset'] as String?;
  final entryDefault = snap['entry_asset_default'] as String?;
  final entryAllowedRaw = snap['entry_assets_allowed'];
  List<String>? entryAllowed;
  if (entryAllowedRaw is List) {
    entryAllowed = entryAllowedRaw.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
  }

  final durationMonths = _durationMonthsFromSnapshot(snap);

  final hasData = apy != null ||
      raised != null ||
      target != null ||
      progress != null ||
      (lendingProductId != null && lendingProductId.isNotEmpty);

  return _LendingFromSnapshot(
    apy: apy,
    raised: raised,
    target: target,
    progress: progress,
    investorsCount: investorsCount,
    durationMonths: durationMonths,
    lendingAsset: asset,
    lendingStatus: status,
    isInvestable: isInvestable,
    lendingProductId: lendingProductId,
    entryAssetDefault: entryDefault,
    entryAssetsAllowed: entryAllowed,
    hasLendingFields: hasData,
  );
}

int? _durationMonthsFromSnapshot(Map<String, dynamic> snap) {
  final startRaw = snap['start_date'];
  final endRaw = snap['maturity_date'];
  if (startRaw is! String || endRaw is! String) return null;
  final start = DateTime.tryParse(startRaw);
  final end = DateTime.tryParse(endRaw);
  if (start == null || end == null) return null;
  final delta = end.difference(start).inDays;
  if (delta <= 0) return null;
  return (delta / 30).round().clamp(1, 600);
}

class _CmsFromVault {
  const _CmsFromVault({
    this.description,
    this.descriptionLinks,
    this.descriptionModuleTitle,
    this.howItWorks,
    this.keyInformation,
    this.competitiveAdvantages,
    this.faq,
    this.bottomPageMarkdown,
  });

  final String? description;
  final List<Map<String, dynamic>>? descriptionLinks;
  final String? descriptionModuleTitle;
  final Map<String, dynamic>? howItWorks;
  final Map<String, dynamic>? keyInformation;
  final Map<String, dynamic>? competitiveAdvantages;
  final Map<String, dynamic>? faq;
  final String? bottomPageMarkdown;
}

_CmsFromVault _parseVaultModules(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return const _CmsFromVault();

  final modules = vaultData['modules'];
  if (modules is! List) return const _CmsFromVault();

  String? description;
  List<Map<String, dynamic>>? descriptionLinks;
  String? descriptionModuleTitle;
  Map<String, dynamic>? howItWorks;
  Map<String, dynamic>? keyInformation;
  Map<String, dynamic>? competitiveAdvantages;
  Map<String, dynamic>? faq;
  final bottomParts = <String>[];

  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final type = (m['type'] ?? m['module'])?.toString() ?? '';

    if (type == 'ContentBasDePageSansModuleBlanc') {
      final content = m['content'];
      if (content is! Map) continue;
      final c = Map<String, dynamic>.from(content);
      final md = (c['markdown'] ?? '').toString().trim();
      if (md.isNotEmpty) bottomParts.add(md);
      continue;
    }

    if (type == 'SimpleMarkdownContentModule') {
      final content = m['content'];
      if (content is! Map) continue;
      final c = Map<String, dynamic>.from(content);
      final moduleTitle = (c['moduleTitle'] ?? '').toString();
      final markdown = (c['markdown'] ?? '').toString();
      final linksRaw = c['links'];
      final links = <Map<String, dynamic>>[];
      if (linksRaw is List) {
        for (final link in linksRaw) {
          if (link is Map) {
            links.add(Map<String, dynamic>.from(link));
          }
        }
      }
      final lower = moduleTitle.toLowerCase();
      final isHow = lower.contains('comment') ||
          lower.contains('fonctionne') ||
          lower.contains('how it works');
      if (isHow) {
        final hiLinks = <Map<String, dynamic>>[];
        for (final l in links) {
          hiLinks.add({'url': l['url'], 'label': l['label']});
        }
        howItWorks = {
          'title': moduleTitle.trim().isNotEmpty ? moduleTitle : 'Comment ça fonctionne',
          'content': markdown,
          'links': hiLinks,
        };
      } else {
        description = markdown.isNotEmpty ? markdown : description;
        descriptionLinks = links.isNotEmpty ? links : descriptionLinks;
        final t = moduleTitle.trim();
        if (t.isNotEmpty) {
          descriptionModuleTitle = t;
        }
      }
      continue;
    }

    if (type == 'CompetitiveAdvantagesModule') {
      final content = m['content'];
      if (content is! Map) continue;
      final c = Map<String, dynamic>.from(content);
      competitiveAdvantages = {
        'title': (c['title'] ?? '').toString(),
        'rows': c['rows'] is List ? c['rows'] : [],
      };
      continue;
    }

    if (type == 'KeyInformationModule') {
      final content = m['content'];
      if (content is! Map) continue;
      final c = Map<String, dynamic>.from(content);
      final rowsIn = c['rows'];
      final rowsOut = <Map<String, dynamic>>[];
      if (rowsIn is List) {
        for (final r in rowsIn) {
          if (r is! Map) continue;
          final row = Map<String, dynamic>.from(r);
          rowsOut.add({
            'label': row['label']?.toString() ?? '',
            'value': row['value']?.toString() ?? '',
            'showInfoIcon': row['showInfoIcon'] == true,
            'infoTitle': row['infoTitle']?.toString() ?? row['infoLinkArticle']?.toString() ?? '',
            'infoContent': row['infoContent']?.toString() ?? '',
          });
        }
      }
      keyInformation = {
        'title': (c['title'] ?? '').toString(),
        'rows': rowsOut,
      };
      continue;
    }

    if (type == 'FaqAccordionModule') {
      final content = m['content'];
      if (content is! Map) continue;
      final c = Map<String, dynamic>.from(content);
      final itemsIn = c['items'];
      final itemsOut = <Map<String, dynamic>>[];
      if (itemsIn is List) {
        for (final it in itemsIn) {
          if (it is! Map) continue;
          final item = Map<String, dynamic>.from(it);
          final question = item['question']?.toString().trim() ?? '';
          final articleSlug = item['articleSlug']?.toString().trim() ?? '';
          final collectionSlug = item['collectionSlug']?.toString().trim() ?? '';
          final categorySlug = item['categorySlug']?.toString().trim() ?? '';
          final standfirst = item['standfirst']?.toString().trim() ?? '';
          if (question.isEmpty || articleSlug.isEmpty || collectionSlug.isEmpty || categorySlug.isEmpty) {
            continue;
          }
          itemsOut.add({
            'question': question,
            'articleSlug': articleSlug,
            'collectionSlug': collectionSlug,
            'categorySlug': categorySlug,
            'standfirst': standfirst,
          });
        }
      }
      if (itemsOut.isNotEmpty) {
        faq = {
          'items': itemsOut,
          if (c['enableTagRedirect'] == true) 'enableTagRedirect': true,
          'tagRedirectLabel': (c['tagRedirectLabel'] ?? c['footerLinkLabel'] ?? '').toString(),
        };
      }
    }
  }

  return _CmsFromVault(
    description: description,
    descriptionLinks: descriptionLinks,
    descriptionModuleTitle: descriptionModuleTitle,
    howItWorks: howItWorks,
    keyInformation: keyInformation,
    competitiveAdvantages: competitiveAdvantages,
    faq: faq,
    bottomPageMarkdown: bottomParts.isEmpty ? null : bottomParts.join('\n\n'),
  );
}

/// URLs vidéo promo depuis le module Vault [TitlePage] (`promoVideoUrls` ou `promoVideoUrl`).
List<String> _parsePromoVideoUrlsFromVault(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return const [];
  final modules = vaultData['modules'];
  if (modules is! List) return const [];
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    if ((m['type'] ?? m['module'])?.toString() != 'TitlePage') continue;
    final content = m['content'];
    if (content is! Map) continue;
    final c = Map<String, dynamic>.from(content);
    final out = <String>[];
    final multi = c['promoVideoUrls'];
    if (multi is List) {
      for (final e in multi) {
        final s = e?.toString().trim() ?? '';
        if (s.isNotEmpty) out.add(s);
      }
    }
    if (out.isEmpty) {
      final single = c['promoVideoUrl']?.toString().trim();
      if (single != null && single.isNotEmpty) out.add(single);
    }
    return List<String>.from(out);
  }
  return const [];
}

String _displayCategory(String? slugOrLabel) {
  final s = slugOrLabel?.trim();
  if (s == null || s.isEmpty) return 'Real estate';
  if (s.contains(' ')) return s;
  return s
      .split(RegExp(r'[-_]'))
      .where((p) => p.isNotEmpty)
      .map((w) => w.length == 1 ? w.toUpperCase() : '${w[0].toUpperCase()}${w.substring(1).toLowerCase()}')
      .join(' ');
}
