import 'dart:ui';

import 'package:flutter/material.dart';

import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';
import '../../../help/data/help_api.dart';
import '../../../help/domain/models/help_center_models.dart';
import '../../../help/presentation/screens/help_articles_screen.dart';
import '../../../landing_preview/data/landing_page_builder_api.dart';
import '../../../markets/data/product_catalog_api.dart';
import '../../../markets/presentation/widgets/bundle_instrument_detail_hero.dart';
import '../../../markets/presentation/widgets/bundle_performance_chart_module.dart';
import '../../../news/data/blog_api.dart';
import '../../../news/domain/models/article_detail.dart';

/// Tranches du module Allocation (CMS) → [ProductAllocationSummary] pour le hero bundle.
List<ProductAllocationSummary> _allocationsFromLandingAllocationModules(
  List<Map<String, dynamic>> modules,
) {
  for (final m in modules) {
    final type = (m['type'] ?? '').toString().trim().toLowerCase();
    final isAlloc = type == 'allocationmodule' ||
        type.contains('allocation') ||
        type.contains('donut');
    if (!isAlloc) continue;
    final content = (m['content'] as Map?)?.cast<String, dynamic>() ?? const {};
    final slicesRaw = (content['slices'] as List?) ?? const [];
    final out = <ProductAllocationSummary>[];
    for (final raw in slicesRaw) {
      if (raw is! Map) continue;
      final e = raw.cast<String, dynamic>();
      final label = (e['label'] ?? '').toString().trim();
      if (label.isEmpty) continue;
      var w = (e['percentage'] is num) ? (e['percentage'] as num).toDouble() : 0.0;
      if (w > 1.0001) w = w / 100.0;
      w = w.clamp(0.0, 1.0);
      final sym = label.toUpperCase();
      out.add(
        ProductAllocationSummary(
          instrumentId: sym,
          instrumentCode: sym,
          name: label,
          assetSymbol: sym,
          targetWeight: w,
        ),
      );
    }
    if (out.isNotEmpty) return out;
  }
  return const [];
}

class LandingPagePreviewScreen extends StatefulWidget {
  const LandingPagePreviewScreen({
    super.key,
    this.initialSlug = '',
    this.controlsEnabled = true,
    this.preloadedPayload,
    this.onRefresh,
    this.onInvestTap,
    this.extraNavBarActions = const [],
    this.useImmersiveExclusiveTemplate = false,
    this.bundleAllocations,
  });

  final String initialSlug;
  final bool controlsEnabled;
  /// Si fourni, utilise ce payload au lieu de fetcher (ex. pour les vaults).
  final LandingPagePayload? preloadedPayload;
  /// Callback pour pull-to-refresh (ex. recharger le vault).
  final Future<void> Function()? onRefresh;
  /// Callback for the hero "Investir" button on product detail pages.
  final VoidCallback? onInvestTap;
  /// Additional navbar actions appended after the JSON-driven rightAction.
  final List<AppTopNavBarAction> extraNavBarActions;

  /// Si true (ex. bundle crypto) : [LayoutPageInstrumentDetail] (fond gris, header clair).
  final bool useImmersiveExclusiveTemplate;

  /// Allocations produit (GET détail) pour empiler les avatars crypto dans le hero bundle.
  final List<ProductAllocationSummary>? bundleAllocations;

  static Future<T?> showAsBottomModal<T>(
    BuildContext context, {
    required String slug,
    bool barrierDismissible = true,
  }) {
    return showGeneralDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      barrierLabel: 'Fermer',
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 260),
      pageBuilder: (context, animation, secondaryAnimation) {
        return LandingPagePreviewScreen(
          initialSlug: slug,
          controlsEnabled: false,
        );
      },
      transitionBuilder: (context, animation, secondaryAnimation, child) {
        final curved = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
          reverseCurve: Curves.easeInCubic,
        );
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 1),
            end: Offset.zero,
          ).animate(curved),
          child: child,
        );
      },
    );
  }

  @override
  State<LandingPagePreviewScreen> createState() => _LandingPagePreviewScreenState();
}

class _LandingPagePreviewScreenState extends State<LandingPagePreviewScreen> {
  final LandingPageBuilderApi _api = LandingPageBuilderApi();
  late final TextEditingController _slugController;
  bool _loading = false;
  String? _error;
  LandingPagePayload? _payload;

  @override
  void initState() {
    super.initState();
    _slugController = TextEditingController(
      text: widget.initialSlug.isNotEmpty ? widget.initialSlug : (widget.preloadedPayload?.slug ?? ''),
    );
    if (widget.preloadedPayload != null) {
      setState(() => _payload = widget.preloadedPayload);
    } else if (widget.initialSlug.trim().isNotEmpty) {
      _load();
    }
  }

  @override
  void dispose() {
    _slugController.dispose();
    super.dispose();
  }

  Future<void> _load({bool forceRefresh = true}) async {
    final slug = _slugController.text.trim();
    if (slug.isEmpty) {
      setState(() {
        _error = 'Entre un slug de landing page.';
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final payload = await _api.fetchBySlug(
        slug,
        draft: true,
        forceRefresh: forceRefresh,
      );
      if (!mounted) return;
      setState(() => _payload = payload);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _handleRedirect(
    String redirectType,
    String? target,
  ) async {
    switch (redirectType) {
      case 'back':
      case 'close':
        if (Navigator.of(context).canPop()) {
          Navigator.of(context).pop();
        }
        return;
      case 'internal':
        if ((target ?? '').trim().isEmpty) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Redirect interne: ${target!.trim()}')),
        );
        return;
      case 'external':
        final raw = (target ?? '').trim();
        if (raw.isEmpty) return;
        final normalized = raw.startsWith('http') ? raw : 'https://$raw';
        final uri = Uri.tryParse(normalized);
        if (uri == null) return;
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
        return;
      default:
        return;
    }
  }

  AppTopNavBarAction? _buildRightAction(Map<String, dynamic> config) {
    final right = (config['rightAction'] as Map?)?.cast<String, dynamic>() ?? const {};
    final iconKey = (right['icon'] ?? 'none').toString();
    final redirectType = (right['redirectType'] ?? 'none').toString();
    final target = (right['target'] ?? '').toString();
    IconData? icon;
    switch (iconKey) {
      case 'favorite':
        icon = Icons.favorite_border_rounded;
        break;
      case 'share':
        icon = Icons.share_rounded;
        break;
      case 'notifications':
        icon = Icons.notifications_none_rounded;
        break;
      default:
        icon = null;
    }
    if (icon == null) return null;
    return AppTopNavBarAction(
      icon: icon,
      onPressed: () => _handleRedirect(redirectType, target),
    );
  }

  Widget _buildKeyInformationModule(Map<String, dynamic> content) {
    final moduleTitle = (content['title'] ?? '').toString().trim();
    final rowsRaw = (content['rows'] as List?) ?? const [];
    final rows = <TableInformationRowData>[];
    for (final raw in rowsRaw) {
      if (raw is! Map) continue;
      final e = raw.cast<String, dynamic>();
      final left = (e['label'] ?? e['left'] ?? '').toString().trim();
      final right = (e['value'] ?? e['right'] ?? '').toString().trim();
      if (left.isEmpty || right.isEmpty) continue;
      final infoLinkArticle = (e['infoLinkArticle'] ?? '').toString().trim();
      final showInfoIcon = e['showInfoIcon'] == true && infoLinkArticle.isNotEmpty;
      rows.add(
        TableInformationRowData(
          left: left,
          right: right,
          showInfoIcon: showInfoIcon,
          onInfoTap: (showInfoIcon && infoLinkArticle.isNotEmpty)
              ? () => _openKeyInfoArticleModal(context, infoLinkArticle)
              : null,
        ),
      );
    }
    if (rows.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
      child: TableInformationModule(
        title: moduleTitle.isEmpty ? null : moduleTitle,
        rows: rows,
        titleTextStyle: AppTypography.sectionTitle.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _buildAllocationModule(Map<String, dynamic> content) {
    final title = (content['title'] ?? '').toString().trim();
    final introText = (content['introText'] ?? '').toString().trim();
    final sizeStr = (content['size'] ?? 'large').toString().trim().toLowerCase();
    final isSmall = sizeStr == 'small';
    final slicesRaw = (content['slices'] as List?) ?? const [];
    final slices = <PortfolioAllocationSlice>[];
    final colors = <Color>[];
    Color? colorFromHex(String? hex) {
      if (hex == null || hex.trim().isEmpty) return null;
      var value = hex.trim().replaceAll('#', '');
      if (value.length == 6) value = 'FF$value';
      if (value.length != 8) return null;
      final colorInt = int.tryParse(value, radix: 16);
      return colorInt != null ? Color(colorInt) : null;
    }
    for (final raw in slicesRaw) {
      if (raw is! Map) continue;
      final e = raw.cast<String, dynamic>();
      final label = (e['label'] ?? '').toString().trim();
      final pct = (e['percentage'] is num) ? (e['percentage'] as num).toDouble() : 0.0;
      if (label.isEmpty) continue;
      slices.add(PortfolioAllocationSlice(label: label, percentage: pct));
      final c = colorFromHex((e['colorHex'] ?? '').toString().trim())
          ?? AppColors.cryptoAssetBrand[label.toUpperCase()];
      if (c != null) colors.add(c);
    }
    if (slices.isEmpty) return const SizedBox.shrink();
    final effectiveSlices = isSmall ? slices.take(4).toList() : slices;
    final effectiveColors = colors.length >= effectiveSlices.length ? colors : null;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title.isNotEmpty) ...[
            Text(
              title,
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          if (isSmall)
            PortfolioAllocationCompactModule(
              slices: effectiveSlices,
              sliceColors: effectiveColors,
            )
          else
            PortfolioAllocationModule(
              introText: introText.isEmpty ? null : introText,
              slices: effectiveSlices,
              sliceColors: effectiveColors,
            ),
        ],
      ),
    );
  }

  Future<void> _openKeyInfoArticleModal(BuildContext context, String articleSlug) async {
    await showGeneralDialog<void>(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Fermer',
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 260),
      pageBuilder: (context, animation, secondaryAnimation) {
        return _KeyInfoArticleModal(
          slug: articleSlug,
          fetchArticle: _fetchArticleBySlug,
          buildHelpContent: (d) => _buildHelpArticleContent(d, includeTitleInContent: false),
          buildArticleContent: (a) => _buildArticleContent(a, includeTitleInContent: false),
        );
      },
      transitionBuilder: (context, animation, secondaryAnimation, dialogChild) {
        final curved = CurvedAnimation(
          parent: animation,
          curve: Curves.easeOutCubic,
          reverseCurve: Curves.easeInCubic,
        );
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 1),
            end: Offset.zero,
          ).animate(curved),
          child: dialogChild,
        );
      },
    );
  }

  /// Récupère un article par slug : essai Help (FAQ) d'abord, puis Blog.
  Future<Object?> _fetchArticleBySlug(String slug) async {
    final help = await HelpApi().getArticleBySlug(slug, locale: 'fr');
    if (help != null) return help;
    final blog = await BlogApi().getArticle(slug, locale: 'fr');
    return blog;
  }

  /// Récupère le contenu FAQ (question + markdown) pour un slug.
  Future<FaqArticleContent?> _fetchFaqArticleContent(String slug) async {
    final data = await _fetchArticleBySlug(slug);
    if (data is HelpArticleDetail) {
      return FaqArticleContent(
        question: data.question,
        markdownContent: data.markdownContent,
      );
    }
    if (data is ArticleDetail) {
      final markdown = data.blocks
          .map((b) {
            if (b.type == 'PARAGRAPH' || b.type == 'QUOTE') {
              return (b.data['text'] ?? '').toString();
            }
            if (b.type == 'HEADING') {
              return '## ${(b.data['text'] ?? '').toString()}';
            }
            return '';
          })
          .where((s) => s.isNotEmpty)
          .join('\n\n');
      return FaqArticleContent(
        question: data.title,
        markdownContent: markdown.isNotEmpty ? markdown : data.standfirst,
      );
    }
    return null;
  }

  Widget _buildHelpArticleContent(HelpArticleDetail detail, {bool includeTitleInContent = true}) {
    final markdown = detail.markdownContent.trim();
    final fallbackText = detail.standfirst.trim().isNotEmpty
        ? detail.standfirst.trim()
        : 'Aucun contenu disponible.';
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (includeTitleInContent && detail.question.trim().isNotEmpty) ...[
            Text(
              detail.question.trim(),
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          if (markdown.isEmpty)
            Text(
              fallbackText,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                height: 1.45,
              ),
            )
          else
            MarkdownBody(
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
                final uri = Uri.tryParse(href.trim());
                if (uri == null) return;
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
              },
            ),
        ],
      ),
    );
  }

  Widget _buildArticleContent(ArticleDetail a, {bool includeTitleInContent = true}) {
    final dateStr = a.publishedAt != null
        ? DateFormat('d MMMM yyyy', 'fr_FR').format(a.publishedAt!)
        : '';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (includeTitleInContent && a.title.trim().isNotEmpty) ...[
          Text(
            a.title.trim(),
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (dateStr.isNotEmpty)
          Text(
            dateStr,
            style: AppTypography.meta.copyWith(color: Colors.grey[500]),
          ),
        if (a.standfirst.trim().isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            a.standfirst,
            style: AppTypography.paragraphLarge.copyWith(
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
              height: 1.5,
            ),
          ),
        ],
        if (a.blocks.isEmpty && a.standfirst.trim().isEmpty)
          Text(
            'Aucun contenu disponible.',
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          )
        else ...[
          const SizedBox(height: 20),
          ...a.blocks.map((b) => _buildArticleBlock(b)),
        ],
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildArticleBlock(ArticleBlock block) {
    switch (block.type) {
      case 'HEADING':
        return Padding(
          padding: const EdgeInsets.only(top: 24, bottom: 12),
          child: Text(
            block.data['text'] as String? ?? '',
            style: AppTypography.headlineSmall.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
        );
      case 'PARAGRAPH':
        final paragraphText = block.data['text'] as String? ?? '';
        if (paragraphText.trim().isEmpty) return const SizedBox.shrink();
        final paragraphStyle = AppTypography.bodyMedium.copyWith(
          height: 1.6,
          color: AppColors.textPrimary,
        );
        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: MarkdownBody(
            data: paragraphText,
            selectable: true,
            onTapLink: (_, href, __) async {
              if (href == null || href.trim().isEmpty) return;
              final uri = Uri.tryParse(href.trim());
              if (uri == null) return;
              try {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              } catch (_) {
                // Lien externe non ouvrable : on ignore (cohérent avec les
                // autres écrans qui ne remontent pas non plus l'erreur à
                // l'utilisateur sur ce type d'action passive).
              }
            },
            styleSheet: MarkdownStyleSheet(
              p: paragraphStyle,
              strong: paragraphStyle.copyWith(fontWeight: FontWeight.w600),
              em: paragraphStyle.copyWith(fontStyle: FontStyle.italic),
              a: paragraphStyle.copyWith(color: AppColors.accent),
              listBullet: paragraphStyle,
              blockSpacing: 0,
              pPadding: EdgeInsets.zero,
            ),
          ),
        );
      case 'QUOTE':
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.pageBackground,
              border: Border(
                left: BorderSide(
                  color: AppColors.accent,
                  width: 4,
                ),
              ),
            ),
            child: Text(
              block.data['text'] as String? ?? '',
              style: AppTypography.paragraphLarge.copyWith(
                fontStyle: FontStyle.italic,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
            ),
          ),
        );
      case 'IMAGE':
        final imageUrl = block.imageUrl ?? block.data['url'] as String? ?? '';
        if (imageUrl.isEmpty) return const SizedBox.shrink();
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(
              imageUrl,
              width: double.infinity,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildModule(Map<String, dynamic> module) {
    final type = (module['type'] ?? '').toString().trim();
    final normalizedType = type.toLowerCase();
    final contentRaw = module['content'];
    final content = contentRaw is Map ? contentRaw.cast<String, dynamic>() : const <String, dynamic>{};

    switch (normalizedType) {
      case 'titlepage':
        final title = (content['title'] ?? '').toString().trim();
        final subtitle = (content['subtitle'] ?? '').toString().trim();
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (title.isNotEmpty)
                Text(
                  title,
                  style: AppTypography.sectionTitle.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              if (subtitle.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.sm),
                Text(
                  subtitle,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ],
          ),
        );
      case 'faqaccordionmodule':
        final moduleTitle = (content['moduleTitle'] ?? content['title'] ?? '').toString().trim();
        final itemsRaw = (content['items'] as List?) ?? const [];
        final items = itemsRaw
            .whereType<Map>()
            .map((e) => e.cast<String, dynamic>())
            .map((e) {
              final slug = (e['articleSlug'] ?? '').toString().trim();
              if (slug.isNotEmpty) {
                return FaqAccordionItemData(articleSlug: slug);
              }
              return FaqAccordionItemData(
                question: (e['question'] ?? '').toString(),
                answer: (e['answer'] ?? '').toString(),
              );
            })
            .where((item) =>
                item.isArticleSlugMode ||
                ((item.question ?? '').trim().isNotEmpty &&
                    (item.answer ?? '').trim().isNotEmpty))
            .toList();
        final footerLinkLabel = (content['footerLinkLabel'] ?? content['linkLabel'] ?? '')
            .toString()
            .trim();
        final footerCollectionSlug =
            (content['footerCollectionSlug'] ?? '').toString().trim();
        final footerCategorySlug =
            (content['footerCategorySlug'] ?? '').toString().trim();
        final footerCollectionTitle =
            (content['footerCollectionTitle'] ?? footerCollectionSlug).toString().trim();
        final footerCategoryTitle =
            (content['footerCategoryTitle'] ?? footerCategorySlug).toString().trim();
        final footerFilterLabel =
            (content['footerFilterLabel'] ?? '').toString().trim();
        final footerLinkUrl = (content['footerLinkUrl'] ??
                content['footerLink'] ??
                content['linkUrl'] ??
                content['ctaUrl'] ??
                content['faqLinkUrl'] ??
                '')
            .toString()
            .trim();
        final hasFooterNav = footerCollectionSlug.isNotEmpty &&
            footerCategorySlug.isNotEmpty &&
            footerLinkLabel.isNotEmpty;
        final hasFooterUrl = footerLinkUrl.trim().isNotEmpty;
        final effectiveFooterLabel = hasFooterNav
            ? footerLinkLabel
            : (hasFooterUrl
                ? (footerLinkLabel.isEmpty ? 'Voir les FAQ' : footerLinkLabel)
                : (footerLinkLabel.isEmpty ? null : footerLinkLabel));
        final effectiveFooterTap = hasFooterNav
            ? () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => HelpArticlesScreen(
                      collectionSlug: footerCollectionSlug,
                      collectionTitle: footerCollectionTitle.isNotEmpty
                          ? footerCollectionTitle
                          : footerCollectionSlug,
                      categorySlug: footerCategorySlug,
                      categoryTitle: footerCategoryTitle.isNotEmpty
                          ? footerCategoryTitle
                          : footerCategorySlug,
                      initialFilterTagLabel: footerFilterLabel.isEmpty
                          ? null
                          : footerFilterLabel,
                    ),
                  ),
                );
              }
            : (hasFooterUrl
                ? () async {
                    final normalized = footerLinkUrl.startsWith('http')
                        ? footerLinkUrl
                        : 'https://$footerLinkUrl';
                    final uri = Uri.tryParse(normalized);
                    if (uri == null) return;
                    if (await canLaunchUrl(uri)) {
                      await launchUrl(uri, mode: LaunchMode.externalApplication);
                    }
                  }
                : null);
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: FaqAccordionModule(
            items: items,
            moduleTitle: moduleTitle.isEmpty ? null : moduleTitle,
            groupedInSingleCard: true,
            footerLinkLabel: effectiveFooterLabel,
            onFooterLinkTap: effectiveFooterTap,
            fetchArticleBySlug: _fetchFaqArticleContent,
            onArticleTap: (slug) => _openKeyInfoArticleModal(context, slug),
          ),
        );
      case 'simplemarkdowncontentmodule':
      case 'simple_markdown_content_module':
      case 'descriptionmodule':
      case 'description_module':
        final moduleTitle = (content['moduleTitle'] ?? content['title'] ?? '').toString().trim();
        final markdown = (content['markdown'] ?? '').toString().trim();
        final linksRaw = (content['links'] as List?) ?? const [];
        final links = linksRaw
            .whereType<Map>()
            .map((e) => e.cast<String, dynamic>())
            .map(
              (e) => (
                label: (e['label'] ?? '').toString().trim(),
                url: (e['url'] ?? '').toString().trim(),
              ),
            )
            .where((e) => e.url.isNotEmpty)
            .toList();
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (moduleTitle.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(
                    moduleTitle,
                    style: AppTypography.sectionTitle.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              Container(
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
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (markdown.isNotEmpty)
                      MarkdownBody(
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
                          final uri = Uri.tryParse(href.trim());
                          if (uri == null) return;
                          if (await canLaunchUrl(uri)) {
                            await launchUrl(uri, mode: LaunchMode.externalApplication);
                          }
                        },
                      )
                    else
                      Text(
                        'Aucun contenu.',
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    if (links.isNotEmpty) const SizedBox(height: AppSpacing.md),
                    ...links.map(
                      (link) => Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                        child: InkWell(
                          onTap: () async {
                            final raw = link.url;
                            final normalized = raw.startsWith('http') ? raw : 'https://$raw';
                            final uri = Uri.tryParse(normalized);
                            if (uri == null) return;
                            if (await canLaunchUrl(uri)) {
                              await launchUrl(uri, mode: LaunchMode.externalApplication);
                            }
                          },
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                link.label.isEmpty ? link.url : link.label,
                                style: AppTypography.labelLarge.copyWith(
                                  color: AppColors.accent,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(width: 6),
                              const Icon(
                                Icons.arrow_forward_ios_rounded,
                                size: 14,
                                color: AppColors.accent,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      case 'videoblockarticlemodule':
      case 'video_block_article_module':
        final moduleTitle = (content['title'] ?? '').toString().trim();
        final itemsRaw = (content['items'] as List?) ?? const [];
        final videoItems = <VideoBlockArticleItemData>[];
        for (final raw in itemsRaw) {
          if (raw is! Map) continue;
          final e = raw.cast<String, dynamic>();
          final t = (e['title'] ?? '').toString().trim();
          var videoUrl = (e['videoUrl'] ?? e['video_url'] ?? '').toString().trim();
          final poster = (e['posterImageUrl'] ?? e['posterUrl'] ?? e['mediaUrl'] ?? e['imageUrl'] ?? '')
              .toString()
              .trim();
          if (t.isEmpty || videoUrl.isEmpty || poster.isEmpty) continue;
          if (!videoUrl.startsWith('http')) {
            videoUrl = 'https://$videoUrl';
          }
          final date = (e['date'] ?? e['dateLabel'] ?? '').toString().trim();
          final vu = videoUrl;
          videoItems.add(
            VideoBlockArticleItemData(
              title: t,
              posterUrl: poster,
              videoUrl: vu,
              dateLabel: date.isEmpty ? null : date,
              onTap: () async {
                final uri = Uri.tryParse(vu);
                if (uri == null) return;
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
              },
            ),
          );
        }
        if (videoItems.isEmpty) {
          return const SizedBox.shrink();
        }
        return VideoBlockArticleModule(
          title: moduleTitle.isEmpty ? 'Vidéos' : moduleTitle,
          items: videoItems,
        );
      case 'localisationmodule':
      case 'localisation_module':
        final titleRaw = (content['moduleTitle'] ?? content['title'] ?? '').toString().trim();
        final description = (content['description'] ?? '').toString().trim();
        final embedUrl = (content['embedUrl'] ?? '').toString().trim();
        if (!LocalisationModule.isAllowedEmbedUrl(embedUrl) && titleRaw.isEmpty && description.isEmpty) {
          return const SizedBox.shrink();
        }
        return LocalisationModule(
          moduleTitle: titleRaw.isEmpty ? 'Localisation' : titleRaw,
          description: description,
          embedUrl: embedUrl,
        );
      case 'allocationmodule':
        return _buildAllocationModule(content);
      case 'competitiveadvantagesmodule':
        final title = (content['title'] ?? '').toString().trim();
        final rows = CompetitiveAdvantagesModule.rowsFromJson(
          (content['rows'] as List?) ?? const [],
        );
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: CompetitiveAdvantagesModule(
            title: title.isEmpty ? null : title,
            rows: rows,
          ),
        );
      case 'marktingcardlargeportrait':
        final heightStr = (content['heightSize'] ?? content['height'] ?? 'large')
            .toString()
            .trim()
            .toLowerCase();
        final heightSize = heightStr == 'small'
            ? MarktingCardLargePortraitHeight.small
            : heightStr == 'medium'
                ? MarktingCardLargePortraitHeight.medium
                : MarktingCardLargePortraitHeight.large;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: MarktingCardLargePortrait(
            imageAssetPath: (content['imageAssetPath'] ?? '').toString().trim().isEmpty
                ? null
                : (content['imageAssetPath'] ?? '').toString().trim(),
            imageUrl: (content['imageUrl'] ?? '').toString().trim().isEmpty
                ? null
                : (content['imageUrl'] ?? '').toString().trim(),
            title: (content['title'] ?? '').toString().trim().isEmpty
                ? 'Marketing card'
                : (content['title'] ?? '').toString(),
            heightSize: heightSize,
          ),
        );
      case 'marketingcardssmallcarouselmodule':
        final items = MarketingCardsSmallCarouselModule.itemsFromJson(
          (content['items'] as List?) ?? const [],
        );
        return MarketingCardsSmallCarouselModule(items: items);
      case 'marketingcardssmallslidingcarrousel_portrait':
        return _buildMarketingCardsSmallSlidingCarrousel(
          content: content,
          isPortrait: true,
        );
      case 'marketingcardssmallslidingcarrousel_paysage':
        return _buildMarketingCardsSmallSlidingCarrousel(
          content: content,
          isPortrait: false,
        );
      case 'transactionlatest10module':
        return TransactionLatest10Module(
          title: (content['title'] ?? 'Latest transactions').toString(),
          walletId: int.tryParse((content['walletId'] ?? '0').toString()) ?? 0,
          limit: int.tryParse((content['limit'] ?? '10').toString()) ?? 10,
        );
      case 'performancechart':
      case 'performance_chart':
      case 'bundleperformancechart':
        final chartTitle = (content['title'] ?? 'Performance').toString().trim();
        final productCode = _payload?.slug ?? widget.initialSlug;
        if (productCode.isEmpty) {
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: BundlePerformanceChartModule(
            productCode: productCode,
            title: chartTitle.isEmpty ? 'Performance' : chartTitle,
          ),
        );
      case 'keyinformationmodule':
      case 'keyinformation':
      case 'key information':
        return _buildKeyInformationModule(content);
      case 'contentbasdepagesansmoduleblanc':
      case 'content_bas_de_page_sans_module_blanc':
        final markdown = (content['markdown'] ?? '').toString().trim();
        if (markdown.isEmpty) {
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: MarkdownBody(
            data: markdown,
            selectable: true,
            styleSheet: MarkdownStyleSheet(
              p: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
                fontSize: 12,
                height: 1.45,
              ),
              a: AppTypography.bodyMedium.copyWith(
                color: AppColors.accent,
                fontSize: 12,
                height: 1.45,
                fontWeight: FontWeight.w500,
              ),
              textAlign: WrapAlignment.center,
              blockSpacing: 10,
            ),
            onTapLink: (text, href, title) async {
              if (href == null || href.trim().isEmpty) return;
              final uri = Uri.tryParse(href.trim());
              if (uri == null) return;
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            },
          ),
        );
      default:
        if (normalizedType.contains('keyinformation')) {
          return _buildKeyInformationModule(content);
        }
        if (normalizedType.contains('allocation') || normalizedType.contains('donut')) {
          return _buildAllocationModule(content);
        }
        return Text(
          'Module non encore mappe en preview runtime.',
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        );
    }
  }

  static const double _marketingPortraitRatio = 1.2;
  static const double _marketingLandscapeRatio = 0.75;

  double? _parseVisibleCardsCount(dynamic value) {
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value.trim().replaceAll(',', '.'));
      return parsed;
    }
    return null;
  }

  /// Produit bundle (hero avec line chart) : retire le module perf du corps, allocation en premier.
  List<Map<String, dynamic>> _orderBundleProductModules(
    List<Map<String, dynamic>> modules,
  ) {
    final withoutChart = modules.where((m) {
      final type = (m['type'] ?? '').toString().trim().toLowerCase();
      return type != 'performancechart' &&
          type != 'performance_chart' &&
          type != 'bundleperformancechart';
    }).toList();
    final allocation = <Map<String, dynamic>>[];
    final rest = <Map<String, dynamic>>[];
    for (final m in withoutChart) {
      final type = (m['type'] ?? '').toString().trim().toLowerCase();
      final isAlloc = type == 'allocationmodule' ||
          type.contains('allocation') ||
          type.contains('donut');
      if (isAlloc) {
        allocation.add(m);
      } else {
        rest.add(m);
      }
    }
    return [...allocation, ...rest];
  }

  double _resolveCardRatio({
    required bool isPortrait,
    required String cardAspectRatio,
  }) {
    final normalized = cardAspectRatio.trim();
    if (normalized.isNotEmpty) {
      final parts = normalized.split(':');
      if (parts.length == 2) {
        final first = double.tryParse(parts[0].trim().replaceAll(',', '.'));
        final second = double.tryParse(parts[1].trim().replaceAll(',', '.'));
        if (first != null && second != null && second != 0) {
          return first / second;
        }
      }
    }
    return isPortrait ? _marketingPortraitRatio : _marketingLandscapeRatio;
  }

  Widget _buildMarketingCardsSmallSlidingCarrousel({
    required Map<String, dynamic> content,
    required bool isPortrait,
  }) {
    final itemsRaw = (content['items'] as List?) ?? const [];
    final configItems = itemsRaw
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .map(
          (e) => MarketingCardItemConfig(
            imageUrl: (e['imageUrl'] ?? '').toString().trim().isEmpty
                ? (isPortrait ? 'https://picsum.photos/600/800' : 'https://picsum.photos/800/600')
                : (e['imageUrl'] ?? '').toString().trim(),
            redirectUrl: (e['redirectUrl'] ?? e['url'] ?? 'https://arquantix.com')
                .toString()
                .trim(),
            title: (e['title'] ?? '').toString().trim().isEmpty
                ? null
                : (e['title'] ?? '').toString().trim(),
            description: (e['description'] ?? '').toString().trim().isEmpty
                ? null
                : (e['description'] ?? '').toString().trim(),
            logoLabel: (e['logoLabel'] ?? '').toString().trim().isEmpty
                ? null
                : (e['logoLabel'] ?? '').toString().trim(),
            buttonLabel: (e['buttonLabel'] ?? '').toString().trim().isEmpty
                ? null
                : (e['buttonLabel'] ?? '').toString().trim(),
          ),
        )
        .toList();
    if (configItems.isEmpty) return const SizedBox.shrink();

    final title = (content['title'] ?? '').toString().trim();
    final useCarousel = content['carousel'] == true;
    final showBullets = content['showBullets'] != false;
    final visibleCardsCount = _parseVisibleCardsCount(content['visibleCardsCount']);
    final cardAspectRatio = (content['cardAspectRatio'] ?? '').toString().trim();

    Future<void> onRedirect(String redirectUrl) async {
      final uri = Uri.tryParse(
        redirectUrl.startsWith('http') ? redirectUrl : 'https://$redirectUrl',
      );
      if (uri == null) return;
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    }

    if (configItems.length == 1) {
      final ratio = _resolveCardRatio(
        isPortrait: isPortrait,
        cardAspectRatio: cardAspectRatio,
      );
      final item = configItems.first;
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = constraints.maxWidth;
            final cardHeight = cardWidth * ratio;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (title.isNotEmpty) ...[
                  AppSectionTitle(title),
                  const SizedBox(height: AppSpacing.md),
                ],
                SizedBox(
                  width: cardWidth,
                  height: cardHeight,
                  child: MarketingCard(
                    imageUrl: item.imageUrl,
                    title: item.title ?? '',
                    description: item.description,
                    logoLabel: item.logoLabel,
                    buttonLabel: item.buttonLabel,
                    onTap: () => onRedirect(item.redirectUrl),
                    onButtonTap: item.buttonLabel != null ? () => onRedirect(item.redirectUrl) : null,
                    size: MarketingCardSize.medium,
                    customHeight: cardHeight,
                    borderRadius: isPortrait ? null : 24,
                  ),
                ),
              ],
            );
          },
        ),
      );
    }

    final mode = useCarousel && showBullets
        ? MarketingCardsMode.carousel
        : MarketingCardsMode.sliding;
    return MarketingCardsModule(
      items: configItems,
      layout: isPortrait ? MarketingCardsLayout.portrait : MarketingCardsLayout.landscape,
      mode: mode,
      title: title.isEmpty ? null : title,
      visibleCardsCount: visibleCardsCount,
      cardAspectRatio: cardAspectRatio.isEmpty ? null : cardAspectRatio,
      onRedirect: onRedirect,
    );
  }

  @override
  Widget build(BuildContext context) {
    final landing = _payload?.config ?? const <String, dynamic>{};
    final navbar = (landing['navbar'] as Map?)?.cast<String, dynamic>() ?? const {};
    final pageTitle = (landing['pageTitle'] as Map?)?.cast<String, dynamic>() ?? const {};
    final pageTitleEnabled = pageTitle['enabled'] == true;
    final pageTitleText = (pageTitle['text'] ?? '').toString().trim();
    final modulesRaw = (landing['modules'] as List?) ?? const [];
    final modules = modulesRaw
        .whereType<Map>()
        .map((e) => e.cast<String, dynamic>())
        .where((e) => e['enabled'] != false)
        .toList();

    final leftIconType = (navbar['leftIconType'] ?? 'back').toString();
    final leftRedirectType = (navbar['leftRedirectType'] ?? 'back').toString();
    final leftTarget = (navbar['leftTarget'] ?? '').toString();
    final rightAction = _buildRightAction(navbar);
    final fixedBottomCta =
        (landing['fixedBottomCta'] as Map?)?.cast<String, dynamic>() ?? const {};
    final fixedBottomCtaEnabled = fixedBottomCta['enabled'] == true;
    final fixedBottomCtaLabel = (fixedBottomCta['label'] ?? '').toString().trim();
    final fixedBottomCtaRedirectType =
        (fixedBottomCta['redirectType'] ?? 'none').toString().trim();
    final fixedBottomCtaTarget = (fixedBottomCta['target'] ?? '').toString().trim();

    final leadingType = switch (leftIconType) {
      'close' => AppTopNavBarLeading.close,
      'none' => AppTopNavBarLeading.back,
      _ => AppTopNavBarLeading.back,
    };

    final titlePageModule = modules.cast<Map<String, dynamic>>().where((m) {
      final type = (m['type'] ?? '').toString().trim().toLowerCase();
      return type == 'titlepage';
    }).toList();
    final titlePageContent = titlePageModule.isNotEmpty
        ? (titlePageModule.first['content'] as Map?)?.cast<String, dynamic>() ?? const {}
        : const <String, dynamic>{};
    final titlePageTitle = (titlePageContent['title'] ?? '').toString().trim();
    final titlePageSubtitle = (titlePageContent['subtitle'] ?? '').toString().trim();
    final effectivePageTitle = titlePageTitle.isNotEmpty
        ? titlePageTitle
        : (pageTitleEnabled ? pageTitleText : '');
    final effectivePageSubtitle = titlePageSubtitle;

    final footerModule = modules.lastWhere(
      (m) {
        final type = (m['type'] ?? '').toString().trim().toLowerCase();
        return type == 'contentbasdepagesansmoduleblanc' ||
            type == 'content_bas_de_page_sans_module_blanc';
      },
      orElse: () => const <String, dynamic>{},
    );
    var contentModules = modules.where((m) {
      final type = (m['type'] ?? '').toString().trim().toLowerCase();
      return type != 'contentbasdepagesansmoduleblanc' &&
          type != 'content_bas_de_page_sans_module_blanc' &&
          type != 'titlepage';
    }).toList();
    if (widget.useImmersiveExclusiveTemplate) {
      contentModules = _orderBundleProductModules(contentModules);
    }
    final contentWidgets = contentModules.map(_buildModule).toList();
    final footerContent = footerModule.isEmpty ? null : _buildModule(footerModule);
    final detailMedia = (landing['detailMediaUrl'] ?? '').toString().trim();
    final headerMedia = (landing['headerMediaUrl'] ?? '').toString().trim();
    final heroMediaUrl = detailMedia.isNotEmpty ? detailMedia : headerMedia;
    final productSlug = (_payload?.slug ?? widget.initialSlug).toString().trim();
    final inferredAllocations = _allocationsFromLandingAllocationModules(modules);
    final mergedBundleAllocations =
        (widget.bundleAllocations != null && widget.bundleAllocations!.isNotEmpty)
            ? widget.bundleAllocations
            : (inferredAllocations.isNotEmpty ? inferredAllocations : null);
    final pageLike = _RuntimeLandingTemplatePage(
      title: effectivePageTitle,
      titleSubtitle: effectivePageSubtitle.isNotEmpty ? effectivePageSubtitle : null,
      leadingType: leadingType,
      onLeadingTap: () => _handleRedirect(leftRedirectType, leftTarget),
      rightAction: rightAction,
      productCode: productSlug,
      content: contentWidgets,
      footerRelativeContent: footerContent,
      fixedBottomCtaEnabled:
          fixedBottomCtaEnabled &&
          fixedBottomCtaLabel.isNotEmpty &&
          fixedBottomCtaRedirectType.isNotEmpty,
      fixedBottomCtaLabel: fixedBottomCtaLabel,
      onFixedBottomCtaTap: () => _handleRedirect(
        fixedBottomCtaRedirectType,
        fixedBottomCtaTarget,
      ),
      onRefresh: widget.onRefresh ?? (widget.preloadedPayload == null ? _load : null),
      heroImageUrl: heroMediaUrl.isNotEmpty ? heroMediaUrl : null,
      onInvestTap: widget.onInvestTap,
      extraNavBarActions: widget.extraNavBarActions,
      useImmersiveExclusiveTemplate: widget.useImmersiveExclusiveTemplate,
      bundleAllocations: mergedBundleAllocations,
    );

    if (!widget.controlsEnabled) {
      if (_loading) {
        return const Scaffold(
          backgroundColor: AppColors.pageBackground,
          body: Center(child: CircularProgressIndicator()),
        );
      }
      if (_payload == null) {
        return Scaffold(
          backgroundColor: AppColors.pageBackground,
          appBar: AppTopNavBar(
            leadingType: AppTopNavBarLeading.back,
            onBackTap: () => Navigator.of(context).pop(),
          ),
          body: Center(
            child: Text(
              _error ?? 'Landing introuvable.',
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.errorText,
              ),
            ),
          ),
        );
      }
      return pageLike;
    }

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Preview landing runtime',
        onBackTap: () => Navigator.of(context).pop(),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.pageEdge,
              AppSpacing.md,
              AppSpacing.pageEdge,
              AppSpacing.md,
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _slugController,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      isDense: true,
                      labelText: 'Slug landing page',
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                FilledButton(
                  onPressed: _loading ? null : _load,
                  child: const Text('Charger'),
                ),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.pageEdge,
                0,
                AppSpacing.pageEdge,
                AppSpacing.md,
              ),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _error!,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.errorText,
                  ),
                ),
              ),
            ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _payload == null
                    ? const Center(child: Text('Charge un slug pour prévisualiser.'))
                    : pageLike,
          ),
        ],
      ),
    );
  }
}

class _RuntimeLandingTemplatePage extends StatefulWidget {
  const _RuntimeLandingTemplatePage({
    required this.title,
    this.titleSubtitle,
    required this.leadingType,
    required this.onLeadingTap,
    required this.rightAction,
    required this.content,
    this.footerRelativeContent,
    this.fixedBottomCtaEnabled = false,
    this.fixedBottomCtaLabel = '',
    this.onFixedBottomCtaTap,
    this.onRefresh,
    this.heroImageUrl,
    /// Slug / code produit (API chart bundle).
    this.productCode = '',
    this.onInvestTap,
    this.extraNavBarActions = const [],
    this.useImmersiveExclusiveTemplate = false,
    this.bundleAllocations,
  });

  final String title;
  final String? titleSubtitle;
  final AppTopNavBarLeading leadingType;
  final VoidCallback onLeadingTap;
  final AppTopNavBarAction? rightAction;
  final List<Widget> content;
  final Widget? footerRelativeContent;
  final bool fixedBottomCtaEnabled;
  final String fixedBottomCtaLabel;
  final VoidCallback? onFixedBottomCtaTap;
  final Future<void> Function()? onRefresh;
  /// When set, uses [LayoutPageLevel2] with hero background instead of plain Scaffold.
  final String? heroImageUrl;
  final String productCode;
  final VoidCallback? onInvestTap;
  final List<AppTopNavBarAction> extraNavBarActions;

  /// Gabarit type bundle crypto ([LayoutPageInstrumentDetail]).
  final bool useImmersiveExclusiveTemplate;

  final List<ProductAllocationSummary>? bundleAllocations;

  @override
  State<_RuntimeLandingTemplatePage> createState() => _RuntimeLandingTemplatePageState();
}

class _RuntimeLandingTemplatePageState extends State<_RuntimeLandingTemplatePage> {
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (widget.useImmersiveExclusiveTemplate) {
      // [LayoutPageInstrumentDetail] gère sa propre barre de navigation au scroll.
      return;
    }
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  Widget _buildScrollableContent(bool hasFixedBottomCta) {
    const double titleToFirstModuleGap = AppSpacing.lg;
    final double moduleGap = DashboardLayoutConstants.moduleGap;
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasTitleSubtitle = (widget.titleSubtitle ?? '').trim().isNotEmpty;
    final hasFooterRelativeContent = widget.footerRelativeContent != null;
    final listView = ListView(
      controller: _scrollController,
      padding: EdgeInsets.only(
        bottom: hasFixedBottomCta ? 168 : AppSpacing.xxl,
      ),
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: AppSpacing.md),
        if (hasTitle) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                AppPageTitle(widget.title),
                if (hasTitleSubtitle) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    widget.titleSubtitle!,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: titleToFirstModuleGap),
        ],
        ...widget.content.expand((w) => [w, SizedBox(height: moduleGap)]),
        if (hasFooterRelativeContent) ...[
          widget.footerRelativeContent!,
          const SizedBox(height: AppSpacing.lg),
        ],
      ],
    );
    if (widget.onRefresh != null) {
      return RefreshIndicator(
        onRefresh: widget.onRefresh!,
        child: listView,
      );
    }
    return listView;
  }

  @override
  Widget build(BuildContext context) {
    final heroUrl = (widget.heroImageUrl ?? '').trim();
    if (widget.useImmersiveExclusiveTemplate) {
      return _buildImmersiveExclusiveLayout();
    }
    if (heroUrl.isNotEmpty) {
      return _buildLayoutPageLevel2(heroUrl);
    }
    return _buildClassicLayout();
  }

  /// Gabarit bundle crypto : fond gris, header clair — aligné sur le détail instrument.
  Widget _buildImmersiveExclusiveLayout() {
    final hasFixedBottomCta =
        widget.fixedBottomCtaEnabled &&
        widget.fixedBottomCtaLabel.trim().isNotEmpty &&
        widget.onFixedBottomCtaTap != null;
    final heroTitle =
        widget.title.trim().isEmpty ? 'Crypto Bundle' : widget.title.trim();

    final navActions = <AppTopNavBarAction>[
      if (widget.rightAction != null) widget.rightAction!,
      ...widget.extraNavBarActions,
    ];

    return BundleInstrumentDetailHero(
      productCode: widget.productCode.trim(),
      title: heroTitle,
      titleDescription: widget.titleSubtitle,
      bundleAllocations: widget.bundleAllocations,
      heroImageUrl: widget.heroImageUrl,
      leadingType: widget.leadingType,
      onLeadingTap: widget.onLeadingTap,
      navBarActions: navActions,
      content: widget.content,
      footerContent: widget.footerRelativeContent,
      fixedBottomCta: hasFixedBottomCta
          ? (label: widget.fixedBottomCtaLabel, onTap: widget.onFixedBottomCtaTap!)
          : null,
      onRefresh: widget.onRefresh,
      onInvestTap: widget.onInvestTap,
    );
  }

  Widget _buildLayoutPageLevel2(String heroUrl) {
    final hasFixedBottomCta =
        widget.fixedBottomCtaEnabled &&
        widget.fixedBottomCtaLabel.trim().isNotEmpty &&
        widget.onFixedBottomCtaTap != null;
    return LayoutPageLevel2(
      heroImageUrl: heroUrl,
      title: widget.title,
      subtitle: widget.titleSubtitle,
      leadingType: widget.leadingType,
      onLeadingTap: widget.onLeadingTap,
      navBarActions: [
        if (widget.rightAction != null) widget.rightAction!,
        ...widget.extraNavBarActions,
      ],
      heroActions: CircleButtonRow(
        items: [
          CircleButtonItem(
            icon: Icons.add_rounded,
            label: 'Investir',
            onTap: widget.onInvestTap ?? () {},
            isPrimary: true,
          ),
          CircleButtonItem(
            icon: Icons.bar_chart_rounded,
            label: 'Stats',
            onTap: () {},
          ),
        ],
      ),
      content: widget.content,
      footerContent: widget.footerRelativeContent,
      fixedBottomCta: hasFixedBottomCta
          ? (label: widget.fixedBottomCtaLabel, onTap: widget.onFixedBottomCtaTap!)
          : null,
      onRefresh: widget.onRefresh,
    );
  }

  Widget _buildClassicLayout() {
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasFixedBottomCta =
        widget.fixedBottomCtaEnabled &&
        widget.fixedBottomCtaLabel.trim().isNotEmpty &&
        widget.onFixedBottomCtaTap != null;
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: widget.leadingType,
        onBackTap: widget.onLeadingTap,
        onCloseTap: widget.onLeadingTap,
        title: hasTitle ? widget.title : null,
        centerTitle: false,
        titleOpacity: hasTitle ? _navTitleOpacity : 0,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        actions: [
          if (widget.rightAction != null) widget.rightAction!,
          ...widget.extraNavBarActions,
        ],
      ),
      body: Stack(
        children: [
          _buildScrollableContent(hasFixedBottomCta),
          ...(hasFixedBottomCta
              ? [
                  Align(
                    alignment: Alignment.bottomCenter,
                    child: _FixedBottomGradientCta(
                      label: widget.fixedBottomCtaLabel,
                      onTap: widget.onFixedBottomCtaTap!,
                    ),
                  ),
                ]
              : []),
        ],
      ),
    );
  }
}

class _FixedBottomGradientCta extends StatelessWidget {
  const _FixedBottomGradientCta({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          width: double.infinity,
          padding: EdgeInsets.fromLTRB(
            AppSpacing.pageEdge,
            2,
            AppSpacing.pageEdge,
            AppSpacing.md + bottomInset,
          ),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                AppColors.pageBackground.withValues(alpha: 0.0),
                AppColors.pageBackground.withValues(alpha: 0.72),
                AppColors.pageBackground.withValues(alpha: 0.94),
              ],
            ),
          ),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.15),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: SizedBox(
              width: double.infinity,
              height: 56,
              child: FilledButton(
                onPressed: onTap,
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.textPrimary,
                  foregroundColor: Colors.white,
                  alignment: Alignment.center,
                  padding: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(999),
                  ),
                  textStyle: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w600,
                    height: 1,
                  ),
                ),
                child: Text(label),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Modale article Key Info : charge l'article, affiche le titre en TitlePage (hors module blanc).
class _KeyInfoArticleModal extends StatefulWidget {
  const _KeyInfoArticleModal({
    required this.slug,
    required this.fetchArticle,
    required this.buildHelpContent,
    required this.buildArticleContent,
  });

  final String slug;
  final Future<Object?> Function(String slug) fetchArticle;
  final Widget Function(HelpArticleDetail) buildHelpContent;
  final Widget Function(ArticleDetail) buildArticleContent;

  @override
  State<_KeyInfoArticleModal> createState() => _KeyInfoArticleModalState();
}

class _KeyInfoArticleModalState extends State<_KeyInfoArticleModal> {
  Object? _article;
  bool _loading = true;
  Object? _error;

  @override
  void initState() {
    super.initState();
    widget.fetchArticle(widget.slug).then((data) {
      if (mounted) {
        setState(() {
          _article = data;
          _loading = false;
        });
      }
    }).catchError((e) {
      if (mounted) {
        setState(() {
          _error = e;
          _loading = false;
        });
      }
    });
  }

  String? get _title {
    if (_article is HelpArticleDetail) {
      final t = (_article as HelpArticleDetail).question.trim();
      return t.isEmpty ? null : t;
    }
    if (_article is ArticleDetail) {
      final t = (_article as ArticleDetail).title.trim();
      return t.isEmpty ? null : t;
    }
    return null;
  }

  Widget get _content {
    if (_loading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.xl),
          child: CircularProgressIndicator(),
        ),
      );
    }
    if (_error != null || _article == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        child: Text(
          'Impossible de charger l\'article.',
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.errorText,
            height: 1.4,
          ),
        ),
      );
    }
    if (_article is HelpArticleDetail) {
      return widget.buildHelpContent(_article as HelpArticleDetail);
    }
    if (_article is ArticleDetail) {
      return widget.buildArticleContent(_article as ArticleDetail);
    }
    return const SizedBox.shrink();
  }

  @override
  Widget build(BuildContext context) {
    return ModaleFullHeightPage(
      title: _title,
      closeLabel: 'Fermer',
      contentInWhiteModule: true,
      child: _content,
    );
  }
}
