/// Projet / offre exclusive (données CMS + enrichissement lending).
class OfferProject {
  final String id;
  final String imageUrl;
  final String title;
  final String category;
  final String? shortDescription;
  final String? description;
  final List<Map<String, dynamic>>? descriptionLinks;
  /// Titre section Vault ([SimpleMarkdownContentModule] → description), ex. sous le hero.
  final String? descriptionModuleTitle;
  final Map<String, dynamic>? howItWorks;
  final Map<String, dynamic>? keyInformation;
  final String? teaserVideoUrl;
  /// Vidéos promo (URLs) — module Vault [TitlePage] `promoVideoUrl` / `promoVideoUrls` ; optionnel.
  final List<String> promoVideoUrls;
  final bool hasGallery;
  final Map<String, dynamic>? competitiveAdvantages;
  final Map<String, dynamic>? faq;

  /// Markdown « bas de page » (Vault [ContentBasDePageSansModuleBlanc]) — sans encart blanc.
  final String? bottomPageMarkdown;

  // Lending enrichment (from lending_pool_products via GET /api/projects)
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

  /// Slug packagé (catalogue) — présent quand la liste vient du Product Registry.
  final String? catalogSlug;

  /// Identifiant `packaged_products.id` côté registry (liste catalogue).
  final String? packagedProductId;

  const OfferProject({
    required this.id,
    required this.imageUrl,
    required this.title,
    required this.category,
    this.shortDescription,
    this.description,
    this.descriptionLinks,
    this.descriptionModuleTitle,
    this.howItWorks,
    this.keyInformation,
    this.teaserVideoUrl,
    this.promoVideoUrls = const [],
    this.hasGallery = false,
    this.competitiveAdvantages,
    this.faq,
    this.bottomPageMarkdown,
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
    this.catalogSlug,
    this.packagedProductId,
  });

  /// True if this project has linked lending product data.
  bool get hasLendingData => target != null && target! > 0;

  /// Progress as a 0.0–1.0 ratio for progress bars.
  double get progressRatio {
    if (progress == null) return 0.0;
    return (progress! / 100.0).clamp(0.0, 1.0);
  }

  /// Formatted raised amount string (e.g. "813 700").
  String get raisedFormatted {
    if (raised == null) return '0';
    final value = raised!.round();
    return _formatNumber(value);
  }

  /// Formatted target amount string (e.g. "10 000 000").
  String get targetFormatted {
    if (target == null) return '0';
    final value = target!.round();
    return _formatNumber(value);
  }

  static String _formatNumber(int value) {
    final str = value.toString();
    final buf = StringBuffer();
    for (var i = 0; i < str.length; i++) {
      if (i > 0 && (str.length - i) % 3 == 0) buf.write('\u202f');
      buf.write(str[i]);
    }
    return buf.toString();
  }
}
