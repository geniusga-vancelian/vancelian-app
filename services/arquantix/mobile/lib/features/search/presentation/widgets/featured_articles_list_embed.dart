import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte chat « featured_articles_list » — Phase 2c.7.
///
/// Émise par les agents `market` / `advisor` (et autres avec accès au
/// tool `show_featured_articles`) pour pousser une **liste d'articles
/// à lire** en complément d'une synthèse texte.
///
/// Visuel : enveloppe `_CardShell` alignée avec [TransactionDetailEmbed]
/// / [InstrumentDetailCardEmbed]. Titre du bloc + 1 à 5 articles
/// (cover 56×56, titre 2 lignes max, date FR). Tap → deep-link
/// `open_article` (slug) → ouverture du lecteur d'article.
///
/// Mode : **complémentaire** (jamais self-contained — le LLM rédige
/// son commentaire au-dessus du widget).
class FeaturedArticlesListEmbed extends StatelessWidget {
  const FeaturedArticlesListEmbed({
    super.key,
    required this.title,
    required this.items,
  });

  final String title;
  final List<AssistanceArticleItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    final visible = items.take(5).toList(growable: false);
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            style: AppTypography.headerTertiary.copyWith(
              color: AppColors.textPrimary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: AppSpacing.sm),
          for (var i = 0; i < visible.length; i++) ...[
            _ArticleRow(item: visible[i]),
            if (i < visible.length - 1)
              const Padding(
                padding: EdgeInsets.symmetric(
                  vertical: AppSpacing.s2,
                ),
                child: Divider(height: 1),
              ),
          ],
        ],
      ),
    );
  }
}

class _ArticleRow extends StatelessWidget {
  const _ArticleRow({required this.item});

  final AssistanceArticleItem item;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: item.hasDeepLink
          ? () => AssistanceDeepLinkResolver.resolve(
                context,
                item.deepLink!,
              )
          : null,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: AppSpacing.xs,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCover(),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.title,
                    style: AppTypography.itemPrimary.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _formatMeta(),
                    style: AppTypography.itemSupporting.copyWith(
                      color: AppColors.textMuted,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            if (item.hasDeepLink) ...[
              const SizedBox(width: AppSpacing.s2),
              Icon(
                Icons.chevron_right,
                color: AppColors.textMuted,
                size: 18,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCover() {
    final resolved = Config.resolveLogoUrl(item.coverUrl);
    if (resolved == null || resolved.isEmpty) {
      return Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: AppColors.pageBackground,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(
          Icons.article_outlined,
          color: AppColors.textMuted,
          size: 22,
        ),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: CachedNetworkImage(
        imageUrl: resolved,
        width: 56,
        height: 56,
        fit: BoxFit.cover,
        placeholder: (_, __) => Container(
          width: 56,
          height: 56,
          color: AppColors.pageBackground,
        ),
        errorWidget: (_, __, ___) => Container(
          width: 56,
          height: 56,
          color: AppColors.pageBackground,
          child: Icon(
            Icons.article_outlined,
            color: AppColors.textMuted,
            size: 22,
          ),
        ),
      ),
    );
  }

  String _formatMeta() {
    final published = item.publishedAt;
    if (published == null) {
      return item.standfirst.isNotEmpty
          ? item.standfirst
          : 'Article';
    }
    final fmt = DateFormat('d MMM y', 'fr_FR').format(published);
    if (item.isFeatured) return 'À la une · $fmt';
    return fmt;
  }
}

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.only(
          topLeft: Radius.zero,
          topRight: Radius.circular(AppRadius.bubble),
          bottomLeft: Radius.circular(AppRadius.bubble),
          bottomRight: Radius.circular(AppRadius.bubble),
        ),
        boxShadow: AppShadow.defaultShadowList,
      ),
      child: child,
    );
  }
}
