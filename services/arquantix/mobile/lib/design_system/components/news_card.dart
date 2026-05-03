import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'ds_news_reading_time.dart';
import 'ds_news_tag.dart';
import 'kalai_icon.dart';

/// Tag image pour [NewsCard] (libellé + couleur de point optionnelle, Figma Tag.tsx).
class NewsCardTag {
  const NewsCardTag(this.label, [this.dotColor]);

  final String label;
  final Color? dotColor;
}

/// Carte d’article / actualité (Figma `NewsCard.tsx` + imports News).
///
/// - Bloc image : hauteur 167, padding h16 v16/8, image radius 12, tags en haut à gauche (gap 6).
/// - Espace image → titre : 8px (padding haut du bloc texte).
/// - Titre : 17 semibold, max 3 lignes.
/// - Temps : [DsNewsReadingTime] (horloge indigo + texte 13 gris).
class NewsCard extends StatelessWidget {
  const NewsCard({
    super.key,
    required this.imageUrl,
    required this.title,
    this.readTimeMinutes = 0,
    this.tags,
    this.badgeLabel,
    this.metaText,
    this.authorName,
    this.onTap,
  });

  final String imageUrl;
  final String title;

  /// Tags multiples sur l’image (prioritaire sur [badgeLabel]).
  final List<NewsCardTag>? tags;

  /// Un seul tag — rétrocompat ; mappé vers [NewsCardTag] si [tags] est vide.
  final String? badgeLabel;

  /// Temps de lecture en minutes. Ignoré si [metaText] est fourni.
  final int readTimeMinutes;

  /// Texte meta personnalisé (ex. date). Si fourni, remplace le temps de lecture.
  final String? metaText;

  /// Nom de l’auteur, affiché après le temps/meta.
  final String? authorName;
  final VoidCallback? onTap;

  static const double _cardRadius = 16;
  /// Hauteur totale du bloc image (Figma `h-[167px]`).
  static const double _imageSectionHeight = 167;
  static const double _imagePaddingL = 16;
  static const double _imagePaddingT = 16;
  static const double _imagePaddingB = 8;
  static const double _imageRadius = 12;
  static const double _tagGap = 6;
  static const double _tagInset = 8;
  static const double _contentPaddingH = 16;
  /// Entre le bas du bloc image et le titre (aéré vs collage direct).
  static const double _contentPaddingTop = 8;
  static const double _contentGap = 8;
  static const double _contentPaddingBottom = 16;

  /// bodyEmphasized : 3 lignes max.
  static const double _titleMinHeight = 22 * 3;

  List<NewsCardTag> get _resolvedTags {
    if (tags != null && tags!.isNotEmpty) return tags!;
    if (badgeLabel != null && badgeLabel!.trim().isNotEmpty) {
      return [NewsCardTag(badgeLabel!.trim())];
    }
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(_cardRadius),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 20,
              spreadRadius: -10,
            ),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildImage(),
            _buildContent(),
          ],
        ),
      ),
    );
  }

  Widget _buildImage() {
    final tagWidgets = _resolvedTags
        .map(
          (t) => DsNewsTag(
            label: t.label,
            dotColor: t.dotColor ?? const Color(0xFFFF383C),
          ),
        )
        .toList();

    return SizedBox(
      height: _imageSectionHeight,
      child: Padding(
        padding: const EdgeInsets.only(
          left: _imagePaddingL,
          right: _imagePaddingL,
          top: _imagePaddingT,
          bottom: _imagePaddingB,
        ),
        child: Stack(
          children: [
            Positioned.fill(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(_imageRadius),
                child: CachedNetworkImage(
                  imageUrl: imageUrl,
                  fit: BoxFit.cover,
                  placeholder: (_, __) => Container(
                    color: AppColors.gray.withValues(alpha: 0.15),
                  ),
                  errorWidget: (_, __, ___) => Container(
                    color: AppColors.gray.withValues(alpha: 0.15),
                    child: const Center(
                      child: KalaiIcon(
                        KalaiIcons.photo,
                        color: AppColors.gray,
                        size: 32,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            if (tagWidgets.isNotEmpty)
              Positioned(
                top: _tagInset,
                left: _tagInset,
                right: _tagInset,
                child: ClipRect(
                  clipBehavior: Clip.hardEdge,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    physics: const NeverScrollableScrollPhysics(),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (var i = 0; i < tagWidgets.length; i++) ...[
                          if (i > 0) const SizedBox(width: _tagGap),
                          tagWidgets[i],
                        ],
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    final showMeta = _hasMetaLine();
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        _contentPaddingH,
        _contentPaddingTop,
        _contentPaddingH,
        _contentPaddingBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ConstrainedBox(
            constraints: const BoxConstraints(minHeight: _titleMinHeight),
            child: Text(
              title,
              style: AppTypography.bodyEmphasized.copyWith(color: AppColors.black),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (showMeta) ...[
            const SizedBox(height: _contentGap),
            _buildMeta(),
          ],
        ],
      ),
    );
  }

  bool _hasMetaLine() {
    if (metaText != null && metaText!.trim().isNotEmpty) return true;
    if (readTimeMinutes > 0) return true;
    if (authorName != null && authorName!.trim().isNotEmpty) return true;
    return false;
  }

  Widget _buildMeta() {
    final metaStyle = AppTypography.itemSupporting.copyWith(
      color: AppColors.gray,
      letterSpacing: -0.08,
      height: 18 / 13,
      fontWeight: FontWeight.w400,
    );

    final hasCustomMeta = metaText != null && metaText!.trim().isNotEmpty;
    final timeLabel = hasCustomMeta ? metaText! : _formatTime(readTimeMinutes);

    if (hasCustomMeta) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(
              timeLabel,
              style: metaStyle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (authorName != null && authorName!.trim().isNotEmpty) ...[
            Text(' · ', style: metaStyle),
            Flexible(
              child: Text(
                authorName!,
                style: metaStyle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      );
    }

    final author = authorName?.trim();
    if (timeLabel.isEmpty && (author == null || author.isEmpty)) {
      return const SizedBox.shrink();
    }
    if (timeLabel.isEmpty && author != null && author.isNotEmpty) {
      return Text(
        author,
        style: metaStyle,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: DsNewsReadingTime(label: timeLabel),
        ),
        if (author != null && author.isNotEmpty) ...[
          Text(' · ', style: metaStyle),
          Flexible(
            child: Text(
              author,
              style: metaStyle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ],
    );
  }

  static String _formatTime(int mins) {
    if (mins <= 0) return '';
    if (mins < 60) return '$mins minute${mins != 1 ? 's' : ''}';
    final h = mins ~/ 60;
    final m = mins % 60;
    if (m == 0) return '$h heure${h != 1 ? 's' : ''}';
    return '${h}h ${m}m';
  }
}
