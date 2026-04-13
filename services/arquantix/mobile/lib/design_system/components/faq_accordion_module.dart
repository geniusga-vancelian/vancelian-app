import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Données pour un item FAQ. Soit [articleSlug] (charge l'article Help), soit [question]+[answer] (legacy).
class FaqAccordionItemData {
  const FaqAccordionItemData({
    this.articleSlug,
    this.question,
    this.answer,
    this.meta,
    this.onOpenArticle,
  });

  final String? articleSlug;
  final String? question;
  final String? answer;
  final String? meta;
  final VoidCallback? onOpenArticle;

  bool get isArticleSlugMode =>
      articleSlug != null && articleSlug!.trim().isNotEmpty;
}

/// Contenu d'un article FAQ chargé par slug.
class FaqArticleContent {
  const FaqArticleContent({required this.question, required this.markdownContent});
  final String question;
  final String markdownContent;
}

/// Module FAQ avec accordéons, aligné avec le style cartes blanches DS.
/// Si les items ont [articleSlug], fournir [fetchArticleBySlug] pour charger le contenu.
/// Si [onArticleTap] est fourni, les rows articleSlug ouvrent une modale au clic (comme Key Information).
class FaqAccordionModule extends StatelessWidget {
  const FaqAccordionModule({
    super.key,
    required this.items,
    this.emptyTitle = 'No FAQ result',
    this.emptyDescription = 'Try another keyword.',
    this.moduleTitle,
    this.footerLinkLabel,
    this.onFooterLinkTap,
    this.groupedInSingleCard = false,
    this.fetchArticleBySlug,
    this.onArticleTap,
  });

  final List<FaqAccordionItemData> items;
  final String emptyTitle;
  final String emptyDescription;
  final String? moduleTitle;
  final String? footerLinkLabel;
  final VoidCallback? onFooterLinkTap;
  final bool groupedInSingleCard;
  final Future<FaqArticleContent?> Function(String slug)? fetchArticleBySlug;
  final void Function(String slug)? onArticleTap;

  @override
  Widget build(BuildContext context) {
    final hasModuleTitle = moduleTitle != null && moduleTitle!.trim().isNotEmpty;
    if (items.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.xl),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: AppColors.textPrimary.withValues(alpha: 0.05),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              emptyTitle,
              style: AppTypography.titleSmall.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              emptyDescription,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    if (groupedInSingleCard) {
      final hasFooterLink =
          footerLinkLabel != null && footerLinkLabel!.trim().isNotEmpty && onFooterLinkTap != null;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (hasModuleTitle)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Text(
                moduleTitle!,
                style: AppTypography.sectionTitle.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          Container(
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
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (int i = 0; i < items.length; i++) _buildFaqTile(items[i]),
                  if (hasFooterLink)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.lg,
                      AppSpacing.md,
                      AppSpacing.lg,
                      AppSpacing.md,
                    ),
                    child: InkWell(
                      onTap: onFooterLinkTap,
                      borderRadius: BorderRadius.circular(8),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            footerLinkLabel!,
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
                ],
              ),
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (int i = 0; i < items.length; i++) ...[
          _buildFaqCard(items[i]),
          if (i < items.length - 1) const SizedBox(height: AppSpacing.md),
        ]
      ],
    );
  }

  Widget _buildFaqTile(FaqAccordionItemData item) {
    if (item.isArticleSlugMode && fetchArticleBySlug != null) {
      return _FaqAccordionTileWithSlug(
        articleSlug: item.articleSlug!,
        fetchArticleBySlug: fetchArticleBySlug!,
        onArticleTap: onArticleTap,
      );
    }
    if (item.question != null && item.answer != null) {
      return _FaqAccordionTile(item: item);
    }
    return const SizedBox.shrink();
  }

  Widget _buildFaqCard(FaqAccordionItemData item) {
    if (item.isArticleSlugMode && fetchArticleBySlug != null) {
      return _FaqAccordionCardWithSlug(
        articleSlug: item.articleSlug!,
        fetchArticleBySlug: fetchArticleBySlug!,
      );
    }
    if (item.question != null && item.answer != null) {
      return _FaqAccordionCard(item: item);
    }
    return const SizedBox.shrink();
  }
}

class _FaqAccordionTileWithSlug extends StatelessWidget {
  const _FaqAccordionTileWithSlug({
    required this.articleSlug,
    required this.fetchArticleBySlug,
    this.onArticleTap,
  });

  final String articleSlug;
  final Future<FaqArticleContent?> Function(String slug) fetchArticleBySlug;
  final void Function(String slug)? onArticleTap;

  @override
  Widget build(BuildContext context) {
    final useModal = onArticleTap != null;
    return FutureBuilder<FaqArticleContent?>(
      future: fetchArticleBySlug(articleSlug),
      builder: (context, snapshot) {
        final content = snapshot.data;
        final question = content?.question ?? articleSlug;
        final markdown = content?.markdownContent ?? '';
        final title = snapshot.connectionState == ConnectionState.waiting
            ? 'Chargement…'
            : question;

        if (useModal) {
          return InkWell(
            onTap: snapshot.connectionState == ConnectionState.waiting
                ? null
                : () => onArticleTap!(articleSlug),
            borderRadius: BorderRadius.zero,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.md,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: AppTypography.titleSmall.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Icon(
                    Icons.chevron_right_rounded,
                    size: 24,
                    color: AppColors.textSecondary,
                  ),
                ],
              ),
            ),
          );
        }

        return Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.xs,
            ),
            childrenPadding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              0,
              AppSpacing.lg,
              AppSpacing.lg,
            ),
            collapsedIconColor: AppColors.textSecondary,
            iconColor: AppColors.textSecondary,
            title: Text(
              title,
              style: AppTypography.titleSmall.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            children: [
              if (snapshot.connectionState == ConnectionState.waiting)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                  child: Center(child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )),
                )
              else if (markdown.isEmpty)
                Text(
                  'Impossible de charger l\'article.',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.errorText,
                  ),
                )
              else
                MarkdownBody(
                  data: markdown,
                  selectable: true,
                  styleSheet: MarkdownStyleSheet(
                    p: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textPrimary,
                      height: 1.4,
                    ),
                    a: AppTypography.bodyMedium.copyWith(
                      color: AppColors.accent,
                      height: 1.4,
                    ),
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
      },
    );
  }
}

class _FaqAccordionCardWithSlug extends StatelessWidget {
  const _FaqAccordionCardWithSlug({
    required this.articleSlug,
    required this.fetchArticleBySlug,
  });

  final String articleSlug;
  final Future<FaqArticleContent?> Function(String slug) fetchArticleBySlug;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<FaqArticleContent?>(
      future: fetchArticleBySlug(articleSlug),
      builder: (context, snapshot) {
        final content = snapshot.data;
        final question = content?.question ?? articleSlug;
        final markdown = content?.markdownContent ?? '';
        return Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: AppColors.textPrimary.withValues(alpha: 0.05),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.xs,
              ),
              childrenPadding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                0,
                AppSpacing.lg,
                AppSpacing.lg,
              ),
              collapsedIconColor: AppColors.textSecondary,
              iconColor: AppColors.textSecondary,
              title: Text(
                snapshot.connectionState == ConnectionState.waiting
                    ? 'Chargement…'
                    : question,
                style: AppTypography.titleSmall.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              children: [
                if (snapshot.connectionState == ConnectionState.waiting)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                    child: Center(child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )),
                  )
                else if (markdown.isEmpty)
                  Text(
                    'Impossible de charger l\'article.',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.errorText,
                    ),
                  )
                else
                  MarkdownBody(
                    data: markdown,
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      p: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textPrimary,
                        height: 1.4,
                      ),
                      a: AppTypography.bodyMedium.copyWith(
                        color: AppColors.accent,
                        height: 1.4,
                      ),
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
          ),
        );
      },
    );
  }
}

class _FaqAccordionCard extends StatelessWidget {
  const _FaqAccordionCard({required this.item});

  final FaqAccordionItemData item;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.xs,
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            0,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          collapsedIconColor: AppColors.textSecondary,
          iconColor: AppColors.textSecondary,
          title: Text(
            item.question ?? '',
            style: AppTypography.titleSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          subtitle: item.meta == null || item.meta!.trim().isEmpty
              ? null
              : Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.xs),
                  child: Text(
                    item.meta!,
                    style: AppTypography.labelSmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
          children: [
            Text(
              item.answer ?? '',
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textPrimary,
                height: 1.4,
              ),
            ),
            if (item.onOpenArticle != null) ...[
              const SizedBox(height: AppSpacing.md),
              Align(
                alignment: Alignment.centerLeft,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: item.onOpenArticle,
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.xs,
                        vertical: AppSpacing.xs,
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Open full article',
                            style: AppTypography.labelLarge.copyWith(
                              color: AppColors.accent,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.chevron_right,
                            size: 20,
                            color: AppColors.accent,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ]
          ],
        ),
      ),
    );
  }
}

class _FaqAccordionTile extends StatelessWidget {
  const _FaqAccordionTile({required this.item});

  final FaqAccordionItemData item;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xs,
        ),
        childrenPadding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          0,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        collapsedIconColor: AppColors.textSecondary,
        iconColor: AppColors.textSecondary,
        title: Text(
          item.question ?? '',
          style: AppTypography.titleSmall.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: item.meta == null || item.meta!.trim().isEmpty
            ? null
            : Padding(
                padding: const EdgeInsets.only(top: AppSpacing.xs),
                child: Text(
                  item.meta!,
                  style: AppTypography.labelSmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
        children: [
          Text(
            item.answer ?? '',
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textPrimary,
              height: 1.4,
            ),
          ),
          if (item.onOpenArticle != null) ...[
            const SizedBox(height: AppSpacing.md),
            Align(
              alignment: Alignment.centerLeft,
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: item.onOpenArticle,
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.xs,
                      vertical: AppSpacing.xs,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Open full article',
                          style: AppTypography.labelLarge.copyWith(
                            color: AppColors.accent,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Icon(
                          Icons.chevron_right,
                          size: 20,
                          color: AppColors.accent,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }
}
