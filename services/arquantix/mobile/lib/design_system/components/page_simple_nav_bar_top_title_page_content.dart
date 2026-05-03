import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_page_title.dart';
import 'app_top_nav_bar.dart';

/// Template de page simple réutilisable:
/// - navbar top avec back + titre compact
/// - titre de page dans le contenu (scrollable)
/// - fade in/out du titre de navbar selon la visibilité du titre de page.
class PageSimpleNavBarTopTitlePageContent extends StatefulWidget {
  const PageSimpleNavBarTopTitlePageContent({
    super.key,
    required this.pageTitle,
    required this.content,
    this.onBackTap,
    this.navBarActions = const [],
    this.backgroundColor = AppColors.pageBackground,
    this.horizontalPadding = const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
    this.contentBottomPadding = AppSpacing.xxl,
    this.titleToContentSpacing = AppSpacing.md,
    this.onRefresh,
    this.fadeStartOffset = 24,
    this.fadeEndOffset = 64,
    this.navBarTitleTextStyle,
  });

  final String pageTitle;
  final List<Widget> content;
  final VoidCallback? onBackTap;
  final List<AppTopNavBarAction> navBarActions;
  final Color backgroundColor;
  final EdgeInsets horizontalPadding;
  final double contentBottomPadding;
  final double titleToContentSpacing;
  final Future<void> Function()? onRefresh;
  final double fadeStartOffset;
  final double fadeEndOffset;
  final TextStyle? navBarTitleTextStyle;

  @override
  State<PageSimpleNavBarTopTitlePageContent> createState() =>
      _PageSimpleNavBarTopTitlePageContentState();
}

class _PageSimpleNavBarTopTitlePageContentState
    extends State<PageSimpleNavBarTopTitlePageContent> {
  final ScrollController _scrollController = ScrollController();
  /// Fade du titre navbar : isolé du corps pour ne pas reconstruire le [ListView]
  /// (évite sur iOS une réinitialisation gênante de la sélection dans les champs).
  final ValueNotifier<double> _navTitleOpacity = ValueNotifier<double>(0);

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    _navTitleOpacity.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - widget.fadeStartOffset) /
            (widget.fadeEndOffset - widget.fadeStartOffset))
        .clamp(0.0, 1.0);
    if ((next - _navTitleOpacity.value).abs() > 0.02) {
      _navTitleOpacity.value = next;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: widget.backgroundColor,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(60),
        child: ValueListenableBuilder<double>(
          valueListenable: _navTitleOpacity,
          builder: (context, opacity, _) {
            return AppTopNavBar(
              leadingType: AppTopNavBarLeading.back,
              title: widget.pageTitle,
              onBackTap: widget.onBackTap,
              centerTitle: false,
              actions: widget.navBarActions,
              titleTextStyle: widget.navBarTitleTextStyle ??
                  AppTypography.paragraph.copyWith(
                    color: AppColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
              titleOpacity: opacity,
            );
          },
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: widget.horizontalPadding,
          child: (widget.onRefresh == null)
              ? ListView(
                  controller: _scrollController,
                  padding: EdgeInsets.only(bottom: widget.contentBottomPadding),
                  children: [
                    const SizedBox(height: AppSpacing.md),
                    AppPageTitle(widget.pageTitle),
                    SizedBox(height: widget.titleToContentSpacing),
                    ...widget.content,
                  ],
                )
              : RefreshIndicator(
                  onRefresh: widget.onRefresh!,
                  child: ListView(
                    controller: _scrollController,
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: EdgeInsets.only(bottom: widget.contentBottomPadding),
                    children: [
                      const SizedBox(height: AppSpacing.md),
                      AppPageTitle(widget.pageTitle),
                      SizedBox(height: widget.titleToContentSpacing),
                      ...widget.content,
                    ],
                  ),
                ),
        ),
      ),
    );
  }
}
