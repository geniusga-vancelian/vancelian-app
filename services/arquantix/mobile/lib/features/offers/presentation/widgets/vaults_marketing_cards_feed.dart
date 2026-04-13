import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';
import '../../data/vaults_api.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import '../../../news/presentation/screens/blog_screen.dart';
import '../../../news/presentation/screens/research_screen.dart';
import '../../../markets/presentation/screens/all_crypto_screen.dart';
import '../../../markets/presentation/widgets/top_crypto_assets_module.dart';
import '../screens/vault_preview_screen.dart';

/// Widget « We get » : charge le feed des modules Marketing Cards Sliding
/// depuis tous les vaults (saving-vaults par défaut) et les affiche dans l'ordre.
class VaultsMarketingCardsFeed extends StatefulWidget {
  const VaultsMarketingCardsFeed({
    super.key,
    this.investmentTypeSlug = 'saving-vaults',
    this.title = 'Vaults',
    this.widgetSlug,
    this.refreshNonce = 0,
    this.assetSlug,
    this.useBlogNewsLayout = false,
  });

  final String? investmentTypeSlug;
  final String title;
  final String? widgetSlug;
  final int refreshNonce;
  /// Filtre crypto pour les widgets dont le feed dépend de l'asset (ex. blog-a-la-une).
  final String? assetSlug;
  /// Si true, affiche les sections blog avec le composant Blog News (compact) au lieu de Blog A la une.
  final bool useBlogNewsLayout;

  @override
  State<VaultsMarketingCardsFeed> createState() => _VaultsMarketingCardsFeedState();
}

class _VaultsMarketingCardsFeedState extends State<VaultsMarketingCardsFeed> {
  final VaultsApi _api = VaultsApi();
  bool _loading = true;
  String? _error;
  List<VaultsMarketingCardsFeedSection> _sections = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant VaultsMarketingCardsFeed oldWidget) {
    super.didUpdateWidget(oldWidget);
    final shouldReload = oldWidget.widgetSlug != widget.widgetSlug ||
        oldWidget.investmentTypeSlug != widget.investmentTypeSlug ||
        oldWidget.refreshNonce != widget.refreshNonce ||
        oldWidget.assetSlug != widget.assetSlug ||
        oldWidget.useBlogNewsLayout != widget.useBlogNewsLayout;
    if (shouldReload) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final sections = (widget.widgetSlug ?? '').trim().isNotEmpty
          ? await _api.getMarketingCardsSectionsFromWidget(
              widget.widgetSlug!.trim(),
              assetSlug: widget.assetSlug,
              cacheBust: widget.refreshNonce != 0 ? widget.refreshNonce : null,
            )
          : await _api.getMarketingCardsFeed(
              investmentTypeSlug: widget.investmentTypeSlug,
            );
      if (!mounted) return;
      setState(() {
        _sections = sections;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _sections = const [];
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _onRedirect(String redirectUrl) async {
    final raw = redirectUrl.trim();
    if (raw.startsWith('vault://')) {
      final slug = raw.substring('vault://'.length).trim();
      if (slug.isNotEmpty) {
        await VaultPreviewScreen.open(context, slug);
      }
      return;
    }
    if (raw.startsWith('blog://')) {
      final slug = raw.substring('blog://'.length).trim();
      if (slug.isNotEmpty && mounted) {
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => ArticleDetailScreen(slug: slug),
          ),
        );
      }
      return;
    }
    if (raw.startsWith('bundle://')) {
      return;
    }
    if (raw.startsWith('/')) {
      final uri = Uri.tryParse(raw);
      final slug = uri?.pathSegments.isNotEmpty == true
          ? uri!.pathSegments.last.trim()
          : '';
      if (slug.isNotEmpty) {
        await VaultPreviewScreen.open(context, slug);
        return;
      }
    }
    final uri = Uri.tryParse(
      redirectUrl.startsWith('http') ? redirectUrl : 'https://$redirectUrl',
    );
    if (uri == null) return;
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _onWidgetHeaderRedirect(String? target) async {
    final normalized = (target ?? '').trim().toLowerCase();
    if (normalized == 'blog' && mounted) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (_) => const BlogScreen(),
        ),
      );
      return;
    }
    if (normalized == 'research' && mounted) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (_) => const ResearchScreen(),
        ),
      );
      return;
    }
    if ((normalized == 'all_crypto' || normalized == 'all-crypto') && mounted) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (_) => const AllCryptoScreen(),
        ),
      );
    }
  }

  bool get _isVancelianTopNewsWidget =>
      (widget.widgetSlug ?? '').trim().toLowerCase() == 'top10news';

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      if (_isVancelianTopNewsWidget) {
        return Padding(
          padding: const EdgeInsets.only(top: AppSpacing.md, bottom: AppSpacing.xl),
          child: VancelianNewsModuleSkeleton(title: widget.title, cardCount: 2),
        );
      }
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpacing.xl),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(color: AppColors.errorText),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Réessayer'),
            ),
          ],
        ),
      );
    }
    if (_sections.isEmpty) {
      // En mode widget (ex. page détail asset), ne pas afficher la section si vide.
      if (widget.widgetSlug != null && widget.widgetSlug!.trim().isNotEmpty) {
        return const SizedBox.shrink();
      }
      return Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.pageEdge,
          vertical: AppSpacing.xl,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            AppSectionTitle(widget.title),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Aucun contenu pour le moment.',
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    final hasBlogSections = _sections.any((s) => s.blogItems.isNotEmpty);
    final firstSection = _sections.first;
    final firstSectionTitle = firstSection.title.isNotEmpty
        ? firstSection.title
        : firstSection.vaultTitle;
    final widgetHeaderTitle = (firstSection.widgetHeaderTitle ?? '').trim();
    final resolvedHeaderTitle = firstSectionTitle.isNotEmpty
        ? firstSectionTitle
        : (widgetHeaderTitle.isNotEmpty ? widgetHeaderTitle : widget.title);
    final shouldRenderExternalHeader = !hasBlogSections && firstSectionTitle.isEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (shouldRenderExternalHeader) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: Builder(
              builder: (context) {
                final headerRedirect = firstSection.widgetHeaderRedirect;
                if ((headerRedirect ?? '').trim().isNotEmpty) {
                  return InkWell(
                    onTap: () => _onWidgetHeaderRedirect(headerRedirect),
                    borderRadius: BorderRadius.circular(8),
                    child: Row(
                      children: [
                        Expanded(child: AppSectionTitle(resolvedHeaderTitle)),
                        const Icon(Icons.chevron_right_rounded, size: 22),
                      ],
                    ),
                  );
                }
                return AppSectionTitle(resolvedHeaderTitle);
              },
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        for (int si = 0; si < _sections.length; si++) ...[
          if (si > 0) const SizedBox(height: DashboardLayoutConstants.moduleGap),
          Builder(builder: (context) {
          final section = _sections[si];
          final displayTitle = section.title.isNotEmpty
              ? section.title
              : section.vaultTitle;
          return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (section.blogItems.isNotEmpty)
                  widget.useBlogNewsLayout
                      ? BlogNews(
                          title: displayTitle.isNotEmpty
                              ? displayTitle
                              : (widgetHeaderTitle.isNotEmpty ? widgetHeaderTitle : widget.title),
                          onTitleTap: (section.widgetHeaderRedirect ?? '').trim().isNotEmpty
                              ? () => _onWidgetHeaderRedirect(section.widgetHeaderRedirect)
                              : null,
                          items: section.blogItems
                              .map(
                                (it) => BlogNewsItem(
                                  title: it.title,
                                  coverUrl: it.coverUrl,
                                  readingTime: it.readingTime,
                                  onTap: () => _onRedirect(it.redirectUrl),
                                ),
                              )
                              .toList(),
                        )
                      : BlogALaUne(
                          title: displayTitle.isNotEmpty
                              ? displayTitle
                              : (widgetHeaderTitle.isNotEmpty ? widgetHeaderTitle : widget.title),
                          onTitleTap: (section.widgetHeaderRedirect ?? '').trim().isNotEmpty
                              ? () => _onWidgetHeaderRedirect(section.widgetHeaderRedirect)
                              : null,
                          items: section.blogItems
                              .map(
                                (it) => BlogALaUneItem(
                                  title: it.title,
                                  coverUrl: it.coverUrl,
                                  readingTime: it.readingTime,
                                  metaText: it.metaText,
                                  authorName: it.authorName,
                                  tag: it.tag,
                                  tags: it.tags != null && it.tags!.isNotEmpty
                                      ? it.tags!
                                          .map((label) => NewsCardTag(label))
                                          .toList(growable: false)
                                      : null,
                                  onTap: () => _onRedirect(it.redirectUrl),
                                ),
                              )
                              .toList(),
                        )
                else if (section.topCryptoPopularItems.isNotEmpty ||
                    section.topCryptoGainersItems.isNotEmpty ||
                    section.topCryptoLosersItems.isNotEmpty)
                  TopCryptoAssetsModule(
                    onSeeMoreTap: (section.topCryptoSeeMoreRedirect ?? '').trim().isNotEmpty
                        ? () => _onWidgetHeaderRedirect(section.topCryptoSeeMoreRedirect)
                        : null,
                    seeMoreLabel: (section.topCryptoSeeMoreLabel ?? '').trim().isNotEmpty
                        ? section.topCryptoSeeMoreLabel!.trim()
                        : 'See more',
                    popularLabel: (section.topCryptoPopularLabel ?? '').trim().isNotEmpty
                        ? section.topCryptoPopularLabel!.trim()
                        : 'Populaires',
                    gainersLabel: (section.topCryptoGainersLabel ?? '').trim().isNotEmpty
                        ? section.topCryptoGainersLabel!.trim()
                        : 'Top Gainers',
                    losersLabel: (section.topCryptoLosersLabel ?? '').trim().isNotEmpty
                        ? section.topCryptoLosersLabel!.trim()
                        : 'Top Losers',
                    popularAssets: section.topCryptoPopularItems
                        .map(
                          (it) => CryptoAssetItem(
                            name: it.name,
                            ticker: it.ticker,
                            price: it.price,
                            variationPercent: it.variationPercent,
                            redirectUrl: it.redirectUrl,
                          ),
                        )
                        .toList(growable: false),
                    gainerAssets: section.topCryptoGainersItems
                        .map(
                          (it) => CryptoAssetItem(
                            name: it.name,
                            ticker: it.ticker,
                            price: it.price,
                            variationPercent: it.variationPercent,
                            redirectUrl: it.redirectUrl,
                          ),
                        )
                        .toList(growable: false),
                    loserAssets: section.topCryptoLosersItems
                        .map(
                          (it) => CryptoAssetItem(
                            name: it.name,
                            ticker: it.ticker,
                            price: it.price,
                            variationPercent: it.variationPercent,
                            redirectUrl: it.redirectUrl,
                          ),
                        )
                        .toList(growable: false),
                    onAssetTap: (asset) async {
                      final redirect = asset.redirectUrl.trim();
                      if (redirect.startsWith('crypto://') && mounted) {
                        final slug = redirect.substring('crypto://'.length).trim();
                        if (slug.isEmpty) return;
                        await Navigator.of(context).pushNamed<void>(
                          '/crypto/$slug',
                          arguments: asset,
                        );
                        return;
                      }
                      if (redirect.isNotEmpty) {
                        await _onRedirect(redirect);
                      }
                    },
                  )
                else if (section.assetsBundleItems.isNotEmpty)
                  AssetsBundlesModule(
                    title: displayTitle.isNotEmpty ? displayTitle : widget.title,
                    items: section.assetsBundleItems
                        .map((it) => it.toAssetsBundleItem(_onRedirect))
                        .toList(),
                    showImageOverlay: section.showImageOverlay ?? false,
                  )
                else
                  MarketingCardsModule(
                    items: section.items,
                    layout: section.isPortrait
                        ? MarketingCardsLayout.portrait
                        : MarketingCardsLayout.landscape,
                    mode: MarketingCardsMode.sliding,
                    title: displayTitle.isNotEmpty ? displayTitle : null,
                    description: section.description,
                    visibleCardsCount: section.visibleCardsCount,
                    cardAspectRatio: section.cardAspectRatio,
                    onRedirect: _onRedirect,
                  ),
              ],
            );
          }),
        ],
      ],
    );
  }
}
