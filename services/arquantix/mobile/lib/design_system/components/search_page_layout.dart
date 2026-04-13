import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_top_nav_bar.dart';

/// Layout de page Search:
/// - body content: texte, search optionnelle, puis liste cliquable
/// - navbar top optionnelle avec bouton retour
class SearchPageLayout extends StatelessWidget {
  const SearchPageLayout({
    super.key,
    required this.title,
    required this.body,
    this.subtitle,
    this.titleTextStyle,
    this.searchBar,
    this.showTopBackNav = false,
    this.onBackTap,
    this.contentPadding = const EdgeInsets.fromLTRB(
      AppSpacing.xl,
      AppSpacing.md,
      AppSpacing.xl,
      0,
    ),
    this.bottomScrollPadding = 140,
    this.onRefresh,
  });

  final String title;
  final String? subtitle;
  final TextStyle? titleTextStyle;
  final Widget? searchBar;
  final Widget body;
  final bool showTopBackNav;
  final VoidCallback? onBackTap;
  final EdgeInsets contentPadding;
  final double bottomScrollPadding;
  final Future<void> Function()? onRefresh;

  @override
  Widget build(BuildContext context) {
    final resolvedTitleStyle =
        titleTextStyle ??
        AppTypography.sectionTitle.copyWith(
          color: AppColors.textPrimary,
          fontSize: (AppTypography.sectionTitle.fontSize ?? 24) - 1,
          fontWeight: FontWeight.w700,
          height: 1.15,
        );
    final topInset = MediaQuery.paddingOf(context).top;
    final overlayHeight = showTopBackNav ? topInset + kToolbarHeight : 0.0;
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: Stack(
        children: [
          Positioned.fill(
            child: SafeArea(
              bottom: false,
              child: (onRefresh == null)
                  ? CustomScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      slivers: [
                        SliverPadding(
                          padding: EdgeInsets.fromLTRB(
                            contentPadding.left,
                            contentPadding.top + (showTopBackNav ? kToolbarHeight : 0),
                            contentPadding.right,
                            contentPadding.bottom,
                          ),
                          sliver: SliverList(
                            delegate: SliverChildListDelegate.fixed([
                              Text(
                                title,
                                style: resolvedTitleStyle,
                              ),
                              if (subtitle != null && subtitle!.trim().isNotEmpty) ...[
                                const SizedBox(height: AppSpacing.sm),
                                Text(
                                  subtitle!,
                                  style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
                                ),
                              ],
                              if (searchBar != null) ...[
                                const SizedBox(height: AppSpacing.lg),
                                searchBar!,
                              ],
                              const SizedBox(height: AppSpacing.lg),
                              body,
                              SizedBox(height: bottomScrollPadding),
                            ]),
                          ),
                        ),
                      ],
                    )
                  : RefreshIndicator(
                      onRefresh: onRefresh!,
                      child: CustomScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        slivers: [
                          SliverPadding(
                            padding: EdgeInsets.fromLTRB(
                              contentPadding.left,
                              contentPadding.top + (showTopBackNav ? kToolbarHeight : 0),
                              contentPadding.right,
                              contentPadding.bottom,
                            ),
                            sliver: SliverList(
                              delegate: SliverChildListDelegate.fixed([
                                Text(
                                  title,
                                  style: resolvedTitleStyle,
                                ),
                                if (subtitle != null && subtitle!.trim().isNotEmpty) ...[
                                  const SizedBox(height: AppSpacing.sm),
                                  Text(
                                    subtitle!,
                                    style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
                                  ),
                                ],
                                if (searchBar != null) ...[
                                  const SizedBox(height: AppSpacing.lg),
                                  searchBar!,
                                ],
                                const SizedBox(height: AppSpacing.lg),
                                body,
                                SizedBox(height: bottomScrollPadding),
                              ]),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ),
          if (showTopBackNav) ...[
            Positioned(
              left: 0,
              right: 0,
              top: 0,
              height: overlayHeight,
              child: ClipRect(
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                  child: Container(
                    color: AppColors.pageBackground.withValues(alpha: 0.72),
                  ),
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              top: 0,
              child: SafeArea(
                bottom: false,
                child: AppTopNavBar(
                  leadingType: AppTopNavBarLeading.back,
                  title: null,
                  onBackTap: onBackTap,
                  actions: const [],
                  backgroundColor: Colors.transparent,
                  foregroundColor: AppColors.textPrimary,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
