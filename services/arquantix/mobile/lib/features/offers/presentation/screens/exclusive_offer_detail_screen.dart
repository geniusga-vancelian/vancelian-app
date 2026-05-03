import 'dart:async';
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../../../l10n/app_localizations.dart';
import '../../../../l10n/app_localizations_en.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../../help/data/help_api.dart';
import '../../../help/domain/models/help_center_models.dart';
import '../../../news/data/blog_api.dart';
import '../../../news/domain/models/article.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import '../../../help/presentation/screens/help_tagged_articles_screen.dart';
import '../../../wallet/presentation/trading_flow_session_guard.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';
import '../../data/catalog_api.dart';
import '../../data/offer_layout_api.dart';
import '../../data/offers_api.dart';
import '../../domain/catalog_offer_mapper.dart';
import '../../domain/models/offer_project.dart';
import '../../domain/models/vault_offer_builder_models.dart';
import 'lending_invest_flow/lending_invest_source_screen.dart';
import 'offer_documents_screen.dart';

/// Sous-titre hero : premier module Vault Builder [TitlePage] (`content.subtitle`).
/// Premier module [StepsModule] du vault (offre exclusive) : titre + étapes pour [StepsModuleWidget].
({String title, String rightLabel, List<StepItem> steps})? stepsModuleFromVault(
  Map<String, dynamic>? vaultData, {
  String Function(int itemCount)? defaultStepsCountLabel,
}) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    if (m['type'] != 'StepsModule') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final title = (content['title'] ?? '').toString().trim();
    final items = StepItem.listFromJson(content['items']);
    if (title.isEmpty || items.isEmpty) return null;
    final rightRaw = (content['rightLabel'] ?? '').toString().trim();
    final rightLabel = rightRaw.isNotEmpty
        ? rightRaw
        : (defaultStepsCountLabel?.call(items.length) ?? '${items.length}');
    return (title: title, rightLabel: rightLabel, steps: items);
  }
  return null;
}

Future<void> _launchExclusiveOfferExternalUrl(String raw) async {
  final u = Uri.tryParse(raw.trim());
  if (u == null) return;
  if (await canLaunchUrl(u)) {
    await launchUrl(u, mode: LaunchMode.externalApplication);
  }
}

/// Module Vault [VideoBlockArticleModule] : cartes poster + ouverture [videoUrl] au tap.
({String title, List<VideoBlockArticleItemData> items})? videoBlockArticleModuleFromVault(
  Map<String, dynamic>? vaultData, {
  String defaultModuleTitle = 'Videos',
}) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final rawType = (m['type'] ?? m['module'])?.toString().trim() ?? '';
    if (rawType.toLowerCase() != 'videoblockarticlemodule') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final title = (content['title'] ?? '').toString().trim();
    final itemsRaw = content['items'];
    if (itemsRaw is! List) return null;
    final out = <VideoBlockArticleItemData>[];
    for (final it in itemsRaw) {
      if (it is! Map) continue;
      final e = Map<String, dynamic>.from(it);
      final t = (e['title'] ?? '').toString().trim();
      final videoUrl = (e['videoUrl'] ?? e['video_url'] ?? '').toString().trim();
      final poster = (e['posterImageUrl'] ?? e['posterUrl'] ?? e['mediaUrl'] ?? e['imageUrl'] ?? '')
          .toString()
          .trim();
      if (t.isEmpty || videoUrl.isEmpty || poster.isEmpty) continue;
      final date = (e['date'] ?? e['dateLabel'] ?? '').toString().trim();
      final vu = videoUrl;
      out.add(
        VideoBlockArticleItemData(
          title: t,
          posterUrl: poster,
          videoUrl: vu,
          dateLabel: date.isEmpty ? null : date,
          onTap: () {
            unawaited(_launchExclusiveOfferExternalUrl(vu));
          },
        ),
      );
    }
    if (out.isEmpty) return null;
    final moduleTitle = title.isNotEmpty ? title : defaultModuleTitle;
    return (title: moduleTitle, items: out);
  }
  return null;
}

/// Module Vault [LocalisationModule] : titre, description, carte Google (embed).
({String moduleTitle, String description, String embedUrl})? localisationModuleFromVault(
  Map<String, dynamic>? vaultData,
) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final rawType = (m['type'] ?? m['module'])?.toString().trim() ?? '';
    if (rawType.toLowerCase() != 'localisationmodule') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final titleRaw = (content['moduleTitle'] ?? content['title'] ?? 'Localisation').toString().trim();
    final moduleTitle = titleRaw.isEmpty ? 'Localisation' : titleRaw;
    final description = (content['description'] ?? '').toString().trim();
    final embedUrl = (content['embedUrl'] ?? '').toString().trim();
    return (moduleTitle: moduleTitle, description: description, embedUrl: embedUrl);
  }
  return null;
}

String? subtitleFromVaultTitlePageModule(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final type = (m['type'] ?? m['module'])?.toString() ?? '';
    if (type != 'TitlePage') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final text = (content['subtitle'] ?? '').toString().trim();
    if (text.isNotEmpty) return text;
    return null;
  }
  return null;
}

/// Même ordre que le Vault Builder : [KeyInformationModule] avant [SimpleMarkdownContentModule].
/// Les layouts DS historiques avaient `description` avant `widget_table_information`.
/// Écart vertical **entre** chaque module du body (spec produit : 40px exactement).
const double _kExclusiveOfferBodyModuleSpacing = AppSpacing.s10;

List<String> _orderKeyInfoBeforeDescription(List<String> order) {
  final iWi = order.indexOf('widget_table_information');
  final iDesc = order.indexOf('description');
  if (iWi < 0 || iDesc < 0 || iWi < iDesc) {
    return order;
  }
  final out = List<String>.from(order);
  out.removeAt(iWi);
  final newDesc = out.indexOf('description');
  out.insert(newDesc, 'widget_table_information');
  return out;
}

/// Page de détail d'une offre exclusive.
/// Hero [ArticleHeroHeader] ; barre de navigation alignée sur [LayoutPageInstrumentDetail] (bundle).
class ExclusiveOfferDetailScreen extends StatefulWidget {
  const ExclusiveOfferDetailScreen({
    super.key,
    required this.project,
    this.autoStartInvest = false,
  });

  final OfferProject project;
  final bool autoStartInvest;

  @override
  State<ExclusiveOfferDetailScreen> createState() => _ExclusiveOfferDetailScreenState();
}

class _ExclusiveOfferDetailScreenState extends State<ExclusiveOfferDetailScreen> {
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  final BlogApi _blogApi = BlogApi();
  final OfferLayoutApi _offerLayoutApi = OfferLayoutApi();
  final OffersApi _offersApi = OffersApi();
  final CatalogApi _catalogApi = CatalogApi();
  final HelpApi _helpApi = HelpApi();
  final FavoritesApi _favoritesApi = FavoritesApi();
  /// Données fusionnées catalogue (vault + snapshot) quand le détail registry est chargé.
  OfferProject? _catalogMerged;
  /// Chapô issu du module [TitlePage] du vault (prioritaire sur [OfferProject.shortDescription]).
  String? _vaultTitlePageHeroSubtitle;
  /// JSON vault brut (modules) pour modules non mappés dans [CatalogOfferMapper], ex. [StepsModule].
  Map<String, dynamic>? _vaultData;
  List<ArticlePreview> _projectNews = const [];
  Map<String, dynamic>? _offerLayout;
  String? _descriptionOverride;
  List<Map<String, dynamic>>? _descriptionLinksOverride;
  Map<String, dynamic>? _competitiveAdvantagesOverride;
  Map<String, dynamic>? _howItWorksOverride;
  Map<String, dynamic>? _keyInformationOverride;
  bool _isFavorite = false;
  String? _favoriteId;

  /// Projet effectif : détail catalogue fusionné si disponible, sinon navigation initiale.
  OfferProject get _p => _catalogMerged ?? widget.project;

  /// Sous le titre hero : priorité au module Vault [TitlePage] (`subtitle`), sinon chapô catalogue.
  String? get _heroDescriptionLine {
    final fromVault = _vaultTitlePageHeroSubtitle?.trim();
    if (fromVault != null && fromVault.isNotEmpty) return fromVault;
    final fromCatalog = _p.shortDescription?.trim();
    if (fromCatalog != null && fromCatalog.isNotEmpty) return fromCatalog;
    return null;
  }

  /// Vidéos promo (Vault TitlePage + repli [teaserVideoUrl] legacy).
  List<String> get _promoVideoUrlsResolved {
    final p = _p;
    if (p.promoVideoUrls.isNotEmpty) return p.promoVideoUrls;
    if (p.teaserVideoUrl != null && p.teaserVideoUrl!.trim().isNotEmpty) {
      return [p.teaserVideoUrl!.trim()];
    }
    return const [];
  }

  Future<void> _openPromoVideos(AppLocalizations l10n, List<String> urls) async {
    if (urls.isEmpty) return;
    if (urls.length == 1) {
      final uri = Uri.tryParse(urls.first);
      if (uri != null && await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
      return;
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
              child: Text(
                l10n.exclusiveOfferVideosTitle,
                style: AppTypography.sectionTitle.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            for (var i = 0; i < urls.length; i++)
              ListTile(
                leading: Icon(Icons.play_circle_outline_rounded, color: AppColors.indigo),
                title: Text(
                  l10n.exclusiveOfferVideoItemTitle(i + 1),
                  style: AppTypography.itemPrimary.copyWith(color: AppColors.textPrimary),
                ),
                onTap: () async {
                  Navigator.of(ctx).pop();
                  final uri = Uri.tryParse(urls[i]);
                  if (uri != null && await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadProjectNews();
    _loadOfferLayout();
    unawaited(
      _refreshProjectCompetitiveAdvantages().then((_) {
        if (mounted) _loadFavoriteStatus();
      }),
    );
    if (widget.autoStartInvest) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) unawaited(_openInvestFlow());
      });
    }
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    // Même logique que [LayoutPageInstrumentDetail._onScroll] (détail bundle).
    final screenH = MediaQuery.sizeOf(context).height;
    const overlap = 16.0; // défaut [ArticleHeroHeader.overlapHeight]
    final heroHeaderHeight = screenH *
            ArticleHeroHeader.kExclusiveOfferBackgroundHeightScreenFraction -
        overlap;
    final start = heroHeaderHeight * 0.10;
    final range = heroHeaderHeight * 0.16;
    final next =
        range > 0 ? ((offset - start) / range).clamp(0.0, 1.0) : 0.0;

    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  /// Même rendu que [LayoutPageInstrumentDetail._buildNavBarWithBlur] ; départ clair sur photo hero.
  static const double _oeNavBlurSigma = 20;

  Widget _buildExclusiveOfferNavBarOverlay(BuildContext context) {
    final t = _navTitleOpacity;
    final sigma = _oeNavBlurSigma * t;
    final fgColor = Color.lerp(Colors.white, AppColors.textPrimary, t)!;

    final navBar = AppTopNavBar(
      leadingType: AppTopNavBarLeading.back,
      onBackTap: () => Navigator.of(context).pop(),
      onCloseTap: () => Navigator.of(context).pop(),
      title: _p.title,
      titleOpacity: t,
      centerTitle: true,
      titleMaxLines: 1,
      titleTextStyle: AppTypography.headerTertiary.copyWith(color: fgColor),
      backgroundColor: Colors.transparent,
      foregroundColor: fgColor,
      useDashboardStyle: false,
      actions: [
        AppTopNavBarAction(
          icon: _isFavorite ? Icons.star_rounded : Icons.star_outline,
          iconColor: _isFavorite ? const Color(0xFFFFB800) : null,
          onPressed: _toggleFavorite,
        ),
      ],
    );

    final layered = t <= 0.01
        ? navBar
        : ClipRect(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma),
              child: Container(
                color: AppColors.pageBackground.withValues(alpha: 0.72 * t),
                child: navBar,
              ),
            ),
          );

    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      height: MediaQuery.paddingOf(context).top + kToolbarHeight,
      child: layered,
    );
  }

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'exclusive_offer');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == _p.id).toList();
      setState(() {
        _isFavorite = match.isNotEmpty;
        _favoriteId = match.isNotEmpty ? match.first.id : null;
      });
    } catch (_) {}
  }

  Future<void> _toggleFavorite() async {
    if (_isFavorite && _favoriteId != null) {
      final ok = await _favoritesApi.removeFavorite(_favoriteId!);
      if (ok && mounted) {
        setState(() {
          _isFavorite = false;
          _favoriteId = null;
        });
      }
    } else {
      final result = await _favoritesApi.addFavorite(
        entityType: 'exclusive_offer',
        entityId: _p.id,
      );
      if (result.isSuccess && result.favorite != null && mounted) {
        setState(() {
          _isFavorite = true;
          _favoriteId = result.favorite!.id;
        });
      } else if (!result.isSuccess && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.messageForUser()),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  @override
  void reassemble() {
    super.reassemble();
    _loadOfferLayout(forceRefresh: true);
    _refreshProjectCompetitiveAdvantages();
  }

  Future<void> _refreshProjectCompetitiveAdvantages() async {
    final slug = widget.project.catalogSlug?.trim();
    if (Config.useCatalogForExclusiveOffers && slug != null && slug.isNotEmpty) {
      try {
        final detail = await _catalogApi.getProductBySlug(slug);
        if (!mounted) return;
        setState(() {
          _catalogMerged = CatalogOfferMapper.mergeWithDetail(widget.project, detail);
          _vaultData = detail.vaultData;
          _vaultTitlePageHeroSubtitle = subtitleFromVaultTitlePageModule(detail.vaultData);
          _descriptionOverride = null;
          _descriptionLinksOverride = null;
          _competitiveAdvantagesOverride = null;
          _howItWorksOverride = null;
          _keyInformationOverride = null;
        });
        return;
      } catch (_) {
        if (!Config.fallbackLegacyProjectsOnCatalogFailure) {
          return;
        }
      }
    }

    try {
      final projects = await _offersApi.getProjects(locale: 'fr', limit: 100);
      final match = projects.where((p) => p.id == widget.project.id).cast<OfferProject?>().firstWhere(
            (p) => p != null,
            orElse: () => null,
          );
      if (!mounted || match == null) return;
      setState(() {
        _catalogMerged = null;
        _vaultData = null;
        _vaultTitlePageHeroSubtitle = null;
        _descriptionOverride = match.description;
        _descriptionLinksOverride = match.descriptionLinks;
        _competitiveAdvantagesOverride = match.competitiveAdvantages;
        _howItWorksOverride = match.howItWorks;
        _keyInformationOverride = match.keyInformation;
      });
    } catch (_) {
      // Garder la donnée initiale si refresh impossible.
    }
  }

  Future<void> _loadProjectNews() async {
    try {
      // Related project section: articles linked via article_projects (not by category).
      final list = await _blogApi.getProjectArticles(_p.id);
      if (mounted) setState(() => _projectNews = list);
    } catch (_) {
      if (mounted) setState(() => _projectNews = const []);
    }
  }

  Future<void> _loadOfferLayout({bool forceRefresh = false}) async {
    try {
      final layout = await _offerLayoutApi.getExclusiveOfferDetailLayout(
        forceRefresh: forceRefresh,
      );
      if (!mounted) return;
      setState(() => _offerLayout = layout);
    } catch (_) {
      if (!mounted) return;
      setState(() => _offerLayout = null);
    }
  }

  Map<String, dynamic>? _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    return null;
  }

  List<dynamic> _asList(dynamic value) {
    if (value is List) return value;
    return const [];
  }

  Future<void> _openInvestFlow() async {
    final project = _p;
    final l10n = AppLocalizations.of(context) ?? AppLocalizationsEn();
    if (!project.isInvestable) {
      Modale.show<void>(
        context,
        ModaleParams(
          title: l10n.exclusiveOfferInvestUnavailableTitle,
          description: project.lendingStatus == 'funded'
              ? l10n.exclusiveOfferInvestUnavailableBodyFunded
              : l10n.exclusiveOfferInvestUnavailableBodyOther,
          secondaryButton: ModaleButtonConfig(
            label: l10n.exclusiveOfferClose,
            onTap: () {},
          ),
        ),
      );
      return;
    }

    if (!await CustomerAccountSessionGuard.ensureActiveAccountOrPrompt(context)) {
      return;
    }
    if (!mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute<bool>(
        builder: (_) => LendingInvestSourceScreen(project: project),
      ),
    );
  }

  void _openArticle(ArticlePreview article) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => ArticleDetailScreen(slug: article.slug),
      ),
    );
  }

  Map<String, dynamic> get _competitiveAdvantagesConfigFromProject =>
      _asMap(_competitiveAdvantagesOverride) ??
      _asMap(_p.competitiveAdvantages) ??
      const {};

  Map<String, dynamic> get _howItWorksConfigFromProject =>
      _asMap(_howItWorksOverride) ?? _asMap(_p.howItWorks) ?? const {};

  Map<String, dynamic> get _keyInformationConfigFromProject =>
      _asMap(_keyInformationOverride) ?? _asMap(_p.keyInformation) ?? const {};

  Map<String, dynamic> get _offerBodyConfig {
    final structure = _asMap(_offerLayout?['structure']);
    final body = _asMap(structure?['body']);
    return body ?? const {};
  }

  Map<String, dynamic> get _offerStructureConfig =>
      _asMap(_offerLayout?['structure']) ?? const {};

  Map<String, dynamic> get _headerConfigFromLayout =>
      _asMap(_offerStructureConfig['header']) ?? const {};

  Map<String, dynamic> get _headerCtaConfig =>
      _asMap(_headerConfigFromLayout['cta']) ?? const {};

  List<String> get _headerSecondaryButtonKeys {
    final raw = _asList(_headerCtaConfig['secondaryButtons']);
    final out = raw.map((e) => e.toString().trim().toLowerCase()).where((e) => e.isNotEmpty).toList();
    return out;
  }

  String get _headerPrimaryButtonLabel {
    final primary = _asMap(_headerCtaConfig['primaryButton']);
    return (primary?['label'] ?? '').toString().trim();
  }

  bool get _headerPrimaryButtonEnabled {
    final primary = _asMap(_headerCtaConfig['primaryButton']);
    if (primary == null) return false;
    final showRaw = primary['show'];
    final show = showRaw is bool ? showRaw : true;
    return show;
  }

  bool _headerHasSecondaryButton(String key) =>
      _headerSecondaryButtonKeys.contains(key.trim().toLowerCase());

  List<String> get _moduleOrderFromLayout {
    final raw = _asList(_offerBodyConfig['modules']);
    final out = raw.map((e) => e.toString().trim()).where((e) => e.isNotEmpty).toList();
    return out;
  }

  Map<String, dynamic> get _tableInformationConfigFromLayout =>
      _asMap(_offerBodyConfig['tableInformation']) ?? const {};

  Map<String, dynamic> get _stepsDateConfigFromLayout {
    final configured = _asMap(_offerBodyConfig['stepsDate']);
    if (configured != null) return configured;
    // Backward compatibility for older layout payloads.
    return _asMap(_offerBodyConfig['steps']) ?? const {};
  }

  Map<String, dynamic> get _allocationConfigFromLayout =>
      _asMap(_offerBodyConfig['allocation']) ?? const {};

  Map<String, dynamic> get _faqConfigFromLayout =>
      _asMap(_offerBodyConfig['faq']) ?? const {};

  Map<String, dynamic> get _faqConfigFromProject =>
      _asMap(_p.faq) ?? const {};

  Map<String, dynamic> get _descriptionConfigFromLayout =>
      _asMap(_offerBodyConfig['description']) ?? const {};

  Map<String, dynamic> get _howItWorksConfigFromLayout =>
      _asMap(_offerBodyConfig['howItWorks']) ?? const {};

  Map<String, dynamic> get _projectNewsConfigFromLayout =>
      _asMap(_offerBodyConfig['projectNews']) ?? const {};

  Map<String, dynamic> get _videoBlockArticleConfigFromLayout =>
      _asMap(_offerBodyConfig['videoBlockArticle']) ?? const {};

  int _asInt(dynamic value, {required int fallback}) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) {
      final parsed = int.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
    return fallback;
  }

  String _normalizeExternalUrl(String value) {
    final raw = value.trim();
    if (raw.isEmpty) return '';
    final lower = raw.toLowerCase();
    if (lower.startsWith('http://') || lower.startsWith('https://')) return raw;
    return 'https://$raw';
  }

  String _deriveLinkLabel(String label, String url) {
    final cleanLabel = label.trim();
    if (cleanLabel.isNotEmpty) return cleanLabel;
    final normalized = _normalizeExternalUrl(url);
    if (normalized.isEmpty) return '';
    final uri = Uri.tryParse(normalized);
    if (uri != null && uri.host.trim().isNotEmpty) {
      return uri.host.replaceFirst(RegExp(r'^www\.'), '');
    }
    return normalized;
  }

  double _asDouble(dynamic value, {required double fallback}) {
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
    return fallback;
  }

  String _formatMilestoneDate(DateTime? date) {
    if (date == null) return '';
    const months = <String>[
      'janvier',
      'fevrier',
      'mars',
      'avril',
      'mai',
      'juin',
      'juillet',
      'aout',
      'septembre',
      'octobre',
      'novembre',
      'decembre',
    ];
    final month = months[(date.month - 1).clamp(0, 11)];
    return '${date.day} $month ${date.year}';
  }

  List<ArticlePreview> _milestoneArticlesAscending() {
    final list = _projectNews.where((article) => article.isMilestone).toList();
    list.sort((a, b) {
      final ad = a.publishedAt;
      final bd = b.publishedAt;
      if (ad == null && bd == null) return a.title.compareTo(b.title);
      if (ad == null) return 1;
      if (bd == null) return -1;
      return ad.compareTo(bd);
    });
    return list;
  }

  List<StepItem> _stepsFromMilestoneArticles(
    List<ArticlePreview> milestones,
    AppLocalizations l10n,
  ) {
    final out = <StepItem>[];
    for (int i = 0; i < milestones.length; i++) {
      final article = milestones[i];
      out.add(
        StepItem(
          index: i + 1,
          dayLabel: l10n.exclusiveOfferStepsMilestoneDay(i + 1),
          date: _formatMilestoneDate(article.publishedAt),
          title: article.title,
          description: article.standfirst,
          tags: const [],
          imageUrl: article.coverUrl.isNotEmpty ? article.coverUrl : _p.imageUrl,
        ),
      );
    }
    return out;
  }

  void _showKeyInformationModal({required String title, required String content}) {
    final l10n = AppLocalizations.of(context) ?? AppLocalizationsEn();
    Modale.show<void>(
      context,
      ModaleParams(
        title: title.trim().isEmpty ? l10n.exclusiveOfferModalInfoDefaultTitle : title.trim(),
        description: content.trim(),
        secondaryButton: ModaleButtonConfig(
          label: l10n.exclusiveOfferClose,
          onTap: () {},
        ),
      ),
    );
  }

  List<TableInformationRowData> _tableInformationRowsFromLayout() {
    final projectRowsRaw = _asList(_keyInformationConfigFromProject['rows']);
    final rows = projectRowsRaw.isNotEmpty
        ? projectRowsRaw
        : _asList(_tableInformationConfigFromLayout['rows']);
    final out = <TableInformationRowData>[];
    for (final raw in rows) {
      if (raw is! Map) continue;
      final left = (raw['label'] ?? '').toString().trim();
      final right = (raw['value'] ?? '').toString().trim();
      if (left.isEmpty || right.isEmpty) continue;
      final showInfoIcon = raw['showInfoIcon'] == true;
      final infoTitle = (raw['infoTitle'] ?? '').toString().trim();
      final infoContent = (raw['infoContent'] ?? '').toString().trim();
      out.add(
        TableInformationRowData(
          left: left,
          right: right,
          showInfoIcon: showInfoIcon,
          onInfoTap: showInfoIcon && infoContent.isNotEmpty
              ? () => _showKeyInformationModal(
                    title: infoTitle,
                    content: infoContent,
                  )
              : null,
        ),
      );
    }
    return out;
  }

  List<PortfolioAllocationSlice> _allocationSlicesFromLayout() {
    final items = _asList(_allocationConfigFromLayout['slices']);
    final out = <PortfolioAllocationSlice>[];
    for (final raw in items) {
      if (raw is! Map<String, dynamic>) continue;
      final label = (raw['label'] ?? '').toString().trim();
      if (label.isEmpty) continue;
      final percentage = _asDouble(raw['percentage'], fallback: -1);
      if (percentage < 0) continue;
      out.add(PortfolioAllocationSlice(label: label, percentage: percentage));
    }
    return out;
  }

  List<Color>? _allocationColorsFromLayout(List<PortfolioAllocationSlice> slices) {
    final items = _asList(_allocationConfigFromLayout['slices']);
    if (items.isEmpty || items.length < slices.length) return null;
    final colors = <Color>[];
    for (int i = 0; i < slices.length; i++) {
      final raw = items[i];
      if (raw is! Map<String, dynamic>) return null;
      final color = CompetitiveAdvantagesModule.colorFromHex(
        (raw['colorHex'] ?? '').toString(),
        fallback: const Color(0xFF374151),
      );
      colors.add(color);
    }
    return colors;
  }

  List<_ProjectFaqArticle> _faqArticlesFromProject() {
    final items = _asList(_faqConfigFromProject['items']);
    final out = <_ProjectFaqArticle>[];
    for (final raw in items) {
      if (raw is! Map) continue;
      final question = (raw['question'] ?? '').toString().trim();
      final articleSlug = (raw['articleSlug'] ?? '').toString().trim();
      final collectionSlug = (raw['collectionSlug'] ?? '').toString().trim();
      final categorySlug = (raw['categorySlug'] ?? '').toString().trim();
      final standfirst = (raw['standfirst'] ?? '').toString().trim();
      if (question.isEmpty ||
          articleSlug.isEmpty ||
          collectionSlug.isEmpty ||
          categorySlug.isEmpty) {
        continue;
      }
      out.add(
        _ProjectFaqArticle(
          question: question,
          standfirst: standfirst,
          articleSlug: articleSlug,
          collectionSlug: collectionSlug,
          categorySlug: categorySlug,
        ),
      );
    }
    return out;
  }

  /// CTA hero : [AppPrimaryButton] medium + bouton rond lecture si vidéo(s) promo.
  Widget? _buildExclusiveOfferHeroBelowTitleActions(AppLocalizations l10n) {
    final primaryLabel = _headerPrimaryButtonLabel.isNotEmpty
        ? _headerPrimaryButtonLabel
        : l10n.exclusiveOfferInvestCtaDefault;
    const ctaHorizontalPadding = AppSpacing.s4;
    final children = <Widget>[];
    if (_headerPrimaryButtonEnabled) {
      children.add(
        AppPrimaryButton(
          label: primaryLabel,
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.primary,
          shrinkWrap: true,
          horizontalPadding: ctaHorizontalPadding,
          leading: const Icon(
            Icons.arrow_upward_rounded,
            size: 18,
            color: AppColors.white,
          ),
          onPressed: () => unawaited(_openInvestFlow()),
        ),
      );
    }
    if (_headerHasSecondaryButton('documents')) {
      children.add(
        AppPrimaryButton(
          label: l10n.exclusiveOfferDocuments,
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.secondary,
          shrinkWrap: true,
          horizontalPadding: ctaHorizontalPadding,
          leading: const Icon(
            Icons.picture_as_pdf_rounded,
            size: 18,
            color: AppColors.black,
          ),
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => OfferDocumentsScreen(projectTitle: _p.title),
              ),
            );
          },
        ),
      );
    }
    if (_headerHasSecondaryButton('gallery') && _p.hasGallery) {
      children.add(
        AppPrimaryButton(
          label: l10n.exclusiveOfferGallery,
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.secondary,
          shrinkWrap: true,
          horizontalPadding: ctaHorizontalPadding,
          leading: const Icon(
            Icons.photo_library_outlined,
            size: 18,
            color: AppColors.black,
          ),
          onPressed: () {},
        ),
      );
    }
    final promos = _promoVideoUrlsResolved;
    if (promos.isNotEmpty) {
      children.add(
        Material(
          color: AppColors.white,
          elevation: 1,
          shadowColor: AppColors.textPrimary.withValues(alpha: 0.12),
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: () => unawaited(_openPromoVideos(l10n, promos)),
            child: const SizedBox(
              width: 48,
              height: 48,
              child: Icon(
                Icons.play_arrow_rounded,
                size: 30,
                color: AppColors.indigo,
              ),
            ),
          ),
        ),
      );
    }
    if (children.isEmpty) return null;
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      alignment: WrapAlignment.start,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: children,
    );
  }

  Future<void> _openFaqArticleModal(_ProjectFaqArticle article) async {
    final l10n = AppLocalizations.of(context) ?? AppLocalizationsEn();
    await ModaleFullHeightPage.show<void>(
      context,
      title: article.question,
      closeLabel: l10n.exclusiveOfferFaqModalClose,
      contentInWhiteModule: true,
      child: FutureBuilder<HelpArticleDetail>(
        future: _helpApi.getArticleDetail(
          collectionSlug: article.collectionSlug,
          categorySlug: article.categorySlug,
          articleSlug: article.articleSlug,
        ),
        builder: (context, snapshot) {
          final loc = AppLocalizations.of(context) ?? AppLocalizationsEn();
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Text(
                loc.exclusiveOfferFaqArticleLoadError,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.errorText,
                  height: 1.4,
                ),
              ),
            );
          }

          final detail = snapshot.data!;
          final markdown = detail.markdownContent.trim();
          final fallbackText = detail.standfirst.trim().isNotEmpty
              ? detail.standfirst.trim()
              : loc.exclusiveOfferFaqArticleEmptyFallback;

          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: markdown.isEmpty
                ? Text(
                    fallbackText,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textPrimary,
                      height: 1.45,
                    ),
                  )
                : MarkdownBody(
                    data: markdown,
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      p: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textPrimary,
                        height: 1.45,
                      ),
                      h1: AppTypography.sectionTitle.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                      h2: AppTypography.titleLarge.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                      h3: AppTypography.titleMedium.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                      a: AppTypography.bodyMedium.copyWith(
                        color: AppColors.accent,
                        height: 1.45,
                      ),
                      blockSpacing: 12,
                    ),
                    onTapLink: (text, href, title) async {
                      if (href == null || href.trim().isEmpty) return;
                      final uri = Uri.tryParse(href);
                      if (uri == null) return;
                      if (await canLaunchUrl(uri)) {
                        await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                  ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context) ?? AppLocalizationsEn();
    final stepsTitle = (_stepsDateConfigFromLayout['title'] ?? '').toString().trim();
    final milestoneArticles = _milestoneArticlesAscending();
    final stepsItems = _stepsFromMilestoneArticles(milestoneArticles, l10n);
    final hasMilestoneSteps = stepsItems.isNotEmpty;
    final stepsRightLabel = l10n.exclusiveOfferStepsCountLabel(stepsItems.length);
    final vaultStepsModule = stepsModuleFromVault(
      _vaultData,
      defaultStepsCountLabel: l10n.exclusiveOfferStepsCountLabel,
    );
    final vaultVideoBlock = videoBlockArticleModuleFromVault(
      _vaultData,
      defaultModuleTitle: l10n.exclusiveOfferVideosTitle,
    );
    final vaultLocalisation = localisationModuleFromVault(_vaultData);
    final videoBlockLayoutTitle = (_videoBlockArticleConfigFromLayout['title'] ?? '').toString().trim();
    final videoBlockTitleResolved = videoBlockLayoutTitle.isNotEmpty
        ? videoBlockLayoutTitle
        : (vaultVideoBlock?.title ?? '');
    final allocationTitle = (_allocationConfigFromLayout['title'] ?? '').toString().trim();
    final allocationIntroText = (_allocationConfigFromLayout['introText'] ?? '').toString().trim();
    final allocationSlices = _allocationSlicesFromLayout();
    final allocationColors = _allocationColorsFromLayout(allocationSlices);
    final compactMaxItems = _asInt(_allocationConfigFromLayout['compactMaxItems'], fallback: 4);
    final compactTake = allocationSlices.isEmpty
        ? 0
        : compactMaxItems.clamp(1, allocationSlices.length);
    final faqTitle = (_faqConfigFromLayout['title'] ?? '').toString().trim();
    final faqReadMoreLabel =
        (_faqConfigFromProject['tagRedirectLabel'] ?? _faqConfigFromLayout['readMoreLabel'] ?? '')
            .toString()
            .trim();
    final faqReadMoreUrl = (_faqConfigFromLayout['readMoreUrl'] ?? '').toString().trim();
    final faqProjectArticles = _faqArticlesFromProject();
    final faqItems = faqProjectArticles
        .map((item) => (question: item.question, answer: item.standfirst))
        .toList();
    final faqTagRedirectEnabled = _faqConfigFromProject['enableTagRedirect'] == true;
    final tableInfoTitle =
        (_keyInformationConfigFromProject['title'] ?? _tableInformationConfigFromLayout['title'] ?? '')
            .toString()
            .trim();
    final tableInfoRows = _tableInformationRowsFromLayout();
    var moduleOrder = _moduleOrderFromLayout;
    if (_p.vaultFunding != null && !moduleOrder.contains('collection_progress')) {
      moduleOrder = ['collection_progress', ...moduleOrder];
    }
    moduleOrder = _orderKeyInfoBeforeDescription(moduleOrder);
    // Si le vault contient [VideoBlockArticleModule] mais que le layout DS n’a pas encore la clé.
    if (vaultVideoBlock != null &&
        vaultVideoBlock.items.isNotEmpty &&
        !moduleOrder.contains('video_block_article')) {
      final iNews = moduleOrder.indexOf('project_news');
      if (iNews >= 0) {
        moduleOrder = [
          ...moduleOrder.sublist(0, iNews),
          'video_block_article',
          ...moduleOrder.sublist(iNews),
        ];
      } else {
        moduleOrder = [...moduleOrder, 'video_block_article'];
      }
    }
    final showVaultLocalisation = vaultLocalisation != null &&
        (LocalisationModule.isAllowedEmbedUrl(vaultLocalisation.embedUrl) ||
            vaultLocalisation.moduleTitle.isNotEmpty ||
            vaultLocalisation.description.isNotEmpty);
    if (showVaultLocalisation && !moduleOrder.contains('localisation')) {
      final iNews = moduleOrder.indexOf('project_news');
      if (iNews >= 0) {
        moduleOrder = [
          ...moduleOrder.sublist(0, iNews),
          'localisation',
          ...moduleOrder.sublist(iNews),
        ];
      } else {
        moduleOrder = [...moduleOrder, 'localisation'];
      }
    }
    final descriptionContent =
        (_descriptionOverride ?? _p.description ?? _descriptionConfigFromLayout['content'] ?? '')
            .toString()
            .trim();
    final descriptionLinksRaw = _descriptionLinksOverride ?? _p.descriptionLinks;
    final descriptionLinks = _asList(descriptionLinksRaw)
        .whereType<Map>()
        .map(
          (raw) => _DescriptionLinkItem(
            url: _normalizeExternalUrl((raw['url'] ?? '').toString()),
            label: _deriveLinkLabel(
              (raw['label'] ?? '').toString(),
              (raw['url'] ?? '').toString(),
            ),
          ),
        )
        .where((link) => link.url.isNotEmpty)
        .toList();
    final bottomPageMarkdown = (_p.bottomPageMarkdown ?? '').trim();
    final howItWorksTitle =
        (_howItWorksConfigFromProject['title'] ?? _howItWorksConfigFromLayout['title'] ?? '')
            .toString()
            .trim();
    final howItWorksContent = (_howItWorksConfigFromProject['content'] ?? '')
        .toString()
        .trim();
    final howItWorksLinks = _asList(_howItWorksConfigFromProject['links'])
        .whereType<Map>()
        .map(
          (raw) => _DescriptionLinkItem(
            url: _normalizeExternalUrl((raw['url'] ?? '').toString()),
            label: _deriveLinkLabel(
              (raw['label'] ?? '').toString(),
              (raw['url'] ?? '').toString(),
            ),
          ),
        )
        .where((link) => link.url.isNotEmpty)
        .toList();
    final projectNewsTitle = (_projectNewsConfigFromLayout['title'] ?? '').toString().trim();
    final competitiveAdvantagesTitle =
        (_competitiveAdvantagesConfigFromProject['title'] ?? '').toString().trim();
    final competitiveAdvantagesRows = CompetitiveAdvantagesModule.rowsFromJson(
      _asList(_competitiveAdvantagesConfigFromProject['rows']),
    );
    final orderedModules = <Widget>[];

    for (final key in moduleOrder) {
      switch (key) {
        case 'collection_progress':
          final vf = _p.vaultFunding;
          if (vf == null) break;
          orderedModules.add(
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
              ),
              child: _CollectionProgressModule(
                model: vf,
                investorsLabel: l10n.exclusiveOfferStepsCountLabel(vf.investorsCount),
              ),
            ),
          );
          break;
        case 'widget_table_information':
          if (tableInfoRows.isNotEmpty) {
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: TableInformationModule(
                  title: tableInfoTitle.isEmpty ? null : tableInfoTitle,
                  rows: tableInfoRows,
                  titleTextStyle: AppTypography.sectionTitle.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            );
          }
          break;
        case 'how_it_works':
          if (howItWorksContent.isNotEmpty || howItWorksLinks.isNotEmpty) {
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (howItWorksTitle.isNotEmpty)
                      Text(
                        howItWorksTitle,
                        style: AppTypography.sectionTitle.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    if (howItWorksTitle.isNotEmpty) const SizedBox(height: AppSpacing.sm),
                    _DescriptionModule(
                      description: howItWorksContent,
                      links: howItWorksLinks,
                    ),
                  ],
                ),
              ),
            );
          }
          break;
        case 'description':
          if (descriptionContent.isNotEmpty || descriptionLinks.isNotEmpty) {
            final descTitle = (_p.descriptionModuleTitle ?? '').trim();
            final showVaultTitle = descTitle.isNotEmpty;
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (showVaultTitle) ...[
                      Text(
                        descTitle,
                        style: AppTypography.sectionTitle.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                    ],
                    _DescriptionModule(
                      description: descriptionContent,
                      links: descriptionLinks,
                      paragraphStyle: AppTypography.bodyEmphasized,
                    ),
                  ],
                ),
              ),
            );
          }
          break;
        case 'competitive_advantages':
          if (competitiveAdvantagesRows.isNotEmpty) {
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: CompetitiveAdvantagesModule(
                  title: competitiveAdvantagesTitle.isNotEmpty
                      ? competitiveAdvantagesTitle
                      : null,
                  rows: competitiveAdvantagesRows,
                ),
              ),
            );
          }
          break;
        case 'steps':
        case 'steps_date':
          if (vaultStepsModule != null && vaultStepsModule.steps.isNotEmpty) {
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: StepsModuleWidget(
                  title: vaultStepsModule.title,
                  rightLabel: vaultStepsModule.rightLabel,
                  horizontalMargin: 0,
                  steps: vaultStepsModule.steps,
                ),
              ),
            );
          } else if (hasMilestoneSteps) {
            orderedModules.add(
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                ),
                child: StepsModuleWidget(
                  title: stepsTitle,
                  rightLabel: stepsRightLabel,
                  horizontalMargin: 0,
                  steps: stepsItems,
                  onStepTap: (index) {
                    if (index < 0 || index >= milestoneArticles.length) return;
                    _openArticle(milestoneArticles[index]);
                  },
                ),
              ),
            );
          }
          break;
        case 'allocation':
          if (allocationSlices.isEmpty) break;
          orderedModules.add(
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (allocationTitle.isNotEmpty)
                    Text(
                      allocationTitle,
                      style: AppTypography.sectionTitle.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  if (allocationTitle.isNotEmpty) const SizedBox(height: AppSpacing.sm),
                  PortfolioAllocationModule(
                    introText: allocationIntroText,
                    slices: allocationSlices,
                    sliceColors: allocationColors,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  if (compactTake > 0)
                    PortfolioAllocationCompactModule(
                      slices: allocationSlices.take(compactTake).toList(),
                      sliceColors: allocationColors,
                    ),
                ],
              ),
            ),
          );
          break;
        case 'faq':
          if (faqItems.isEmpty) break;
          orderedModules.add(
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
              ),
              child: _FaqModule(
                title: faqTitle.isEmpty ? l10n.exclusiveOfferFaqDefaultTitle : faqTitle,
                readMoreLabel: faqReadMoreLabel,
                readMoreUrl: faqReadMoreUrl,
                onReadMoreTap: faqTagRedirectEnabled
                    ? () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => HelpTaggedArticlesScreen(
                              tagType: 'EXCLUSIVE_OFFER',
                              tagId: _p.id,
                              title: faqReadMoreLabel,
                            ),
                          ),
                        );
                      }
                    : null,
                onItemTap: faqProjectArticles.isNotEmpty
                    ? (index) {
                        if (index < 0 || index >= faqProjectArticles.length) return;
                        _openFaqArticleModal(faqProjectArticles[index]);
                      }
                    : null,
                items: faqItems,
              ),
            ),
          );
          break;
        case 'project_news':
          if (_projectNews.isNotEmpty && projectNewsTitle.isNotEmpty) {
            orderedModules.add(
              BlogALaUne(
                title: projectNewsTitle,
                items: _projectNews
                    .map(
                      (a) => BlogALaUneItem(
                        title: a.title,
                        coverUrl: a.coverUrl,
                        readingTime: a.readingTime,
                        onTap: () => _openArticle(a),
                        tag: a.categorySlugs?.isNotEmpty == true ? a.categorySlugs!.first : null,
                      ),
                    )
                    .toList(),
              ),
            );
          }
          break;
        case 'video_block_article':
          if (vaultVideoBlock != null && vaultVideoBlock.items.isNotEmpty) {
            orderedModules.add(
              VideoBlockArticleModule(
                title: videoBlockTitleResolved.isNotEmpty
                    ? videoBlockTitleResolved
                    : vaultVideoBlock.title,
                items: vaultVideoBlock.items,
              ),
            );
          }
          break;
        case 'localisation':
          if (!showVaultLocalisation) break;
          orderedModules.add(
            LocalisationModule(
              moduleTitle: vaultLocalisation.moduleTitle,
              description: vaultLocalisation.description,
              embedUrl: vaultLocalisation.embedUrl,
            ),
          );
          break;
        default:
          break;
      }
    }

    final heroBelowTitle = _buildExclusiveOfferHeroBelowTitleActions(l10n);

    final scrollChild = SingleChildScrollView(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ArticleHeroHeader(
            imageUrl: _p.imageUrl,
            title: _p.title,
            subtitle: _heroDescriptionLine,
            badges: [
              for (var i = 0; i < _p.vaultHeroTags.length; i++)
                ArticleCategoryBadgeData(
                  label: _p.vaultHeroTags[i],
                  dotColor: i.isEven ? AppColors.accent : AppColors.gray,
                ),
            ],
            showNavBar: false,
            belowTitle: heroBelowTitle,
            backgroundHeightScreenFraction:
                ArticleHeroHeader.kExclusiveOfferBackgroundHeightScreenFraction,
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.s8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (orderedModules.isNotEmpty)
                  const SizedBox(height: _kExclusiveOfferBodyModuleSpacing),
                for (int i = 0; i < orderedModules.length; i++) ...[
                  orderedModules[i],
                  if (i < orderedModules.length - 1)
                    const SizedBox(height: _kExclusiveOfferBodyModuleSpacing),
                ],
                if (bottomPageMarkdown.isNotEmpty) ...[
                  if (orderedModules.isNotEmpty)
                    const SizedBox(height: _kExclusiveOfferBodyModuleSpacing),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
                    ),
                    child: MarkdownBody(
                      data: bottomPageMarkdown,
                      selectable: true,
                      styleSheet: MarkdownStyleSheet(
                        p: AppTypography.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.45,
                        ),
                        a: AppTypography.bodySmall.copyWith(
                          color: AppColors.accent,
                          height: 1.45,
                          decoration: TextDecoration.underline,
                        ),
                        blockSpacing: 8,
                      ),
                      onTapLink: (text, href, title) async {
                        if (href == null || href.trim().isEmpty) return;
                        final uri = Uri.tryParse(href);
                        if (uri == null) return;
                        if (await canLaunchUrl(uri)) {
                          await launchUrl(uri, mode: LaunchMode.externalApplication);
                        }
                      },
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.xxl),
              ],
            ),
          ),
        ],
      ),
    );

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      extendBodyBehindAppBar: true,
      body: Stack(
        clipBehavior: Clip.none,
        children: [
          RefreshIndicator(
            onRefresh: () async {
              await _loadOfferLayout(forceRefresh: true);
              await _refreshProjectCompetitiveAdvantages();
              await _loadProjectNews();
              await _loadFavoriteStatus();
            },
            child: scrollChild,
          ),
          _buildExclusiveOfferNavBarOverlay(context),
        ],
      ),
    );
  }
}

/// Bloc funding — données [VaultFundingUiModel] (Vault Builder `FundingModule` + lending).
class _CollectionProgressModule extends StatelessWidget {
  const _CollectionProgressModule({
    required this.model,
    required this.investorsLabel,
  });

  final VaultFundingUiModel model;
  final String investorsLabel;

  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _progressBarHeight = 6;

  @override
  Widget build(BuildContext context) {
    final title = model.moduleTitle?.trim();

    final cardBody = <Widget>[];
    if (model.showProgressSection) {
      cardBody.add(
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Flexible(
              child: Text(
                model.raisedAmount,
                style: AppTypography.sectionTitle.copyWith(fontSize: 22),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Text(
              investorsLabel,
              style: AppTypography.meta,
            ),
          ],
        ),
      );
      if (model.progressLabel.isNotEmpty) {
        cardBody.add(const SizedBox(height: AppSpacing.xs));
        cardBody.add(
          Text(
            model.progressLabel,
            style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
          ),
        );
      }
      cardBody.add(const SizedBox(height: AppSpacing.xs));
      cardBody.add(
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: model.progress.clamp(0.0, 1.0),
            minHeight: _progressBarHeight,
            backgroundColor: AppColors.placeholderBg,
            valueColor: const AlwaysStoppedAnimation<Color>(AppColors.textPrimary),
          ),
        ),
      );
    }

    if (model.showAprRow) {
      if (cardBody.isNotEmpty) cardBody.add(const SizedBox(height: AppSpacing.sm));
      cardBody.add(
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (model.aprLabel.isNotEmpty)
              Expanded(
                child: Text(
                  model.aprLabel,
                  style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
                ),
              )
            else
              const Spacer(),
            Text(
              model.aprValue,
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
            ),
          ],
        ),
      );
    }

    if (model.showTargetRow) {
      if (cardBody.isNotEmpty) cardBody.add(const SizedBox(height: AppSpacing.sm));
      cardBody.add(
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (model.targetLabel.isNotEmpty)
              Expanded(
                child: Text(
                  model.targetLabel,
                  style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
                ),
              )
            else
              const Spacer(),
            Text(
              model.totalFundingAmount,
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
            ),
          ],
        ),
      );
    }

    final card = Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _horizontalPadding,
          vertical: _verticalPadding,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: cardBody,
        ),
      ),
    );

    final foot = model.footnoteMarkdown?.trim();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (title != null && title.isNotEmpty) ...[
          Text(
            title,
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        card,
        if (foot != null && foot.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          MarkdownBody(
            data: foot,
            styleSheet: MarkdownStyleSheet(
              p: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
                height: 1.45,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// Ligne de lien — Figma **button/Emphasized** ([AppTypography.buttonEmphasized]), alignée à gauche.
class _LinkRow extends StatelessWidget {
  const _LinkRow({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final linkStyle = AppTypography.buttonEmphasized.copyWith(color: AppColors.accent);
    return Align(
      alignment: Alignment.centerLeft,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: linkStyle,
                  textAlign: TextAlign.start,
                ),
                const SizedBox(width: 6),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 16,
                  color: AppColors.accent,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Module blanc : description du projet (texte ou Markdown) + bouton « Lire les T&Cs ».
class _DescriptionLinkItem {
  const _DescriptionLinkItem({
    required this.label,
    required this.url,
  });

  final String label;
  final String url;
}

class _ProjectFaqArticle {
  const _ProjectFaqArticle({
    required this.question,
    required this.standfirst,
    required this.collectionSlug,
    required this.categorySlug,
    required this.articleSlug,
  });

  final String question;
  final String standfirst;
  final String collectionSlug;
  final String categorySlug;
  final String articleSlug;
}

/// Module blanc : description du projet (texte markdown) + liens optionnels.
class _DescriptionModule extends StatelessWidget {
  const _DescriptionModule({
    required this.description,
    this.links = const [],
    this.paragraphStyle,
  });

  final String description;
  final List<_DescriptionLinkItem> links;

  /// Par défaut [AppTypography.bodyMedium] ; module « description » offre exclusive → [AppTypography.bodyEmphasized].
  final TextStyle? paragraphStyle;

  static const double _horizontalPadding = 20;
  static const double _verticalPadding = 16;
  static const double _spaceBetweenTextAndButton = 16;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: _horizontalPadding,
          vertical: _verticalPadding,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            MarkdownBody(
              data: description,
              styleSheet: MarkdownStyleSheet(
                p: (paragraphStyle ?? AppTypography.bodyMedium)
                    .copyWith(color: AppColors.textPrimary),
                h1: AppTypography.titleLarge.copyWith(color: AppColors.textPrimary),
                h2: AppTypography.titleMedium.copyWith(color: AppColors.textPrimary),
                h3: AppTypography.titleSmall.copyWith(color: AppColors.textPrimary),
                a: AppTypography.buttonEmphasized.copyWith(
                  color: AppColors.accent,
                  decoration: TextDecoration.none,
                ),
                listIndent: 24,
              ),
              onTapLink: (text, href, title) async {
                if (href == null || href.trim().isEmpty) return;
                final uri = Uri.tryParse(href);
                if (uri == null) return;
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
              },
              selectable: true,
            ),
            if (links.isNotEmpty) ...[
              const SizedBox(height: _spaceBetweenTextAndButton),
              ...links.asMap().entries.map((entry) {
                final index = entry.key;
                final link = entry.value;
                return Padding(
                  padding: EdgeInsets.only(bottom: index == links.length - 1 ? 0 : AppSpacing.sm),
                  child: _LinkRow(
                    label: link.label,
                    onTap: () async {
                      final uri = Uri.tryParse(link.url);
                      if (uri == null) return;
                      if (await canLaunchUrl(uri)) {
                        await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}

/// Module FAQ : titre + liste d’items accordéon (question + réponse dépliable).
class _FaqModule extends StatelessWidget {
  const _FaqModule({
    required this.title,
    required this.readMoreLabel,
    required this.readMoreUrl,
    required this.items,
    this.onReadMoreTap,
    this.onItemTap,
  });

  final String title;
  final String readMoreLabel;
  final String readMoreUrl;
  final List<({String question, String answer})> items;
  final VoidCallback? onReadMoreTap;
  final ValueChanged<int>? onItemTap;

  static const double _cardRadius = 24;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(_cardRadius),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                for (var i = 0; i < items.length; i++)
                  _FaqAccordionItem(
                    question: items[i].question,
                    answer: items[i].answer,
                    inline: true,
                    enableExpansion: onItemTap == null,
                    onTap: onItemTap != null ? () => onItemTap!(i) : null,
                  ),
                if (readMoreLabel.trim().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(left: 20, top: 8),
                    child: _LinkRow(
                      label: readMoreLabel,
                      onTap: onReadMoreTap ??
                          () async {
                            if (readMoreUrl.trim().isEmpty) return;
                            final uri = Uri.tryParse(readMoreUrl);
                            if (uri == null) return;
                            if (await canLaunchUrl(uri)) {
                              await launchUrl(uri, mode: LaunchMode.externalApplication);
                            }
                          },
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// Un item FAQ : bloc blanc type transaction (question + caret à droite), au clic la caret tourne 90° et le bloc s’agrandit pour afficher la réponse.
class _FaqAccordionItem extends StatefulWidget {
  const _FaqAccordionItem({
    required this.question,
    required this.answer,
    this.inline = false,
    this.enableExpansion = true,
    this.onTap,
  });

  final String question;
  final String answer;
  /// À true, pas de carte individuelle (utilisé dans le module FAQ unique).
  final bool inline;
  final bool enableExpansion;
  final VoidCallback? onTap;

  @override
  State<_FaqAccordionItem> createState() => _FaqAccordionItemState();
}

class _FaqAccordionItemState extends State<_FaqAccordionItem> with SingleTickerProviderStateMixin {
  bool _expanded = false;
  late AnimationController _controller;
  late Animation<double> _chevronTurns;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 250),
      vsync: this,
    );
    _chevronTurns = Tween<double>(begin: 0, end: 0.25).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    if (widget.onTap != null) {
      widget.onTap!.call();
      return;
    }
    if (!widget.enableExpansion) return;
    setState(() {
      _expanded = !_expanded;
      if (_expanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  static const double _cardRadius = 24;
  static const double _horizontalPadding = 20;
  static const double _horizontalPaddingRightInline = 12;
  static const double _verticalPadding = 16;
  static const double _answerTopPadding = 8;

  Widget _buildContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Text(
                widget.question,
                style: AppTypography.titleSmall.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                  height: 1.3,
                ),
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 12),
            widget.enableExpansion
                ? AnimatedBuilder(
                    animation: _chevronTurns,
                    builder: (context, child) {
                      return Transform.rotate(
                        angle: _chevronTurns.value * 2 * 3.14159265359,
                        child: const Icon(
                          Icons.chevron_right,
                          size: 24,
                          color: AppColors.textSecondary,
                        ),
                      );
                    },
                  )
                : const Icon(
                    Icons.chevron_right,
                    size: 24,
                    color: AppColors.textSecondary,
                  ),
          ],
        ),
        if (widget.enableExpansion)
          SizeTransition(
            sizeFactor: _controller,
            axisAlignment: 0,
            child: FadeTransition(
              opacity: _controller,
              child: Padding(
                padding: const EdgeInsets.only(top: _answerTopPadding),
                child: Text(
                  widget.answer,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final content = Padding(
      padding: EdgeInsets.only(
        left: _horizontalPadding,
        right: widget.inline ? _horizontalPaddingRightInline : _horizontalPadding,
        top: _verticalPadding,
        bottom: _verticalPadding,
      ),
      child: _buildContent(),
    );
    if (widget.inline) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: _toggle,
          borderRadius: BorderRadius.circular(8),
          child: content,
        ),
      );
    }
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: _toggle,
        borderRadius: BorderRadius.circular(_cardRadius),
        child: Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(_cardRadius),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.06),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: content,
        ),
      ),
    );
  }
}
