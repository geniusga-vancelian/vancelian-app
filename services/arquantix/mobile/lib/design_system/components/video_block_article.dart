import 'dart:math' as math;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../core/config.dart';
import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../layout/module_horizontal_margin.dart';
import 'carousel_pagination_dots.dart';
import 'ds_news_reading_time.dart';

/// Donnée d’une carte vidéo (Vault module [VideoBlockArticleModule]).
class VideoBlockArticleItemData {
  const VideoBlockArticleItemData({
    required this.title,
    required this.posterUrl,
    required this.videoUrl,
    this.dateLabel,
    this.onTap,
  });

  final String title;
  /// Image de fond (poster) — URL absolue ou résolue via [Config.resolveLogoUrl].
  final String posterUrl;
  /// Lien vidéo (YouTube, Vimeo, fichier…) ouvert au tap.
  final String videoUrl;
  final String? dateLabel;
  final VoidCallback? onTap;
}

/// Carte « vidéo mise en avant » : poster + bouton lecture au centre, titre et date en dessous.
/// Aligné sur les proportions [NewsCard] (zone image 167px).
class VideoBlockArticle extends StatelessWidget {
  const VideoBlockArticle({
    super.key,
    required this.item,
    this.onTap,
  });

  final VideoBlockArticleItemData item;
  final VoidCallback? onTap;

  static const double _cardRadius = 16;
  static const double _imageSectionHeight = 167;
  static const double _imagePaddingL = 16;
  static const double _imagePaddingT = 16;
  static const double _imagePaddingB = 8;
  static const double _imageRadius = 12;
  static const double _contentPaddingH = 16;
  static const double _contentPaddingTop = 8;
  static const double _contentGap = 8;
  static const double _contentPaddingBottom = 16;
  static const double _titleMinHeight = 22 * 3;

  String get _resolvedPoster {
    final r = Config.resolveLogoUrl(item.posterUrl.trim());
    return (r != null && r.isNotEmpty) ? r : item.posterUrl.trim();
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
            SizedBox(
              height: _imageSectionHeight,
              child: Padding(
                padding: const EdgeInsets.only(
                  left: _imagePaddingL,
                  right: _imagePaddingL,
                  top: _imagePaddingT,
                  bottom: _imagePaddingB,
                ),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(_imageRadius),
                      child: CachedNetworkImage(
                        imageUrl: _resolvedPoster,
                        fit: BoxFit.cover,
                        placeholder: (_, __) => Container(
                          color: AppColors.gray.withValues(alpha: 0.15),
                        ),
                        errorWidget: (_, __, ___) => Container(
                          color: AppColors.gray.withValues(alpha: 0.15),
                          child: const Center(
                            child: Icon(
                              Icons.videocam_outlined,
                              color: AppColors.gray,
                              size: 32,
                            ),
                          ),
                        ),
                      ),
                    ),
                    Positioned.fill(
                      child: Material(
                        color: Colors.black.withValues(alpha: 0.22),
                        borderRadius: BorderRadius.circular(_imageRadius),
                        child: const SizedBox.expand(),
                      ),
                    ),
                    Center(
                      child: SvgPicture.asset(
                        'assets/images/video_play_circle.svg',
                        width: 61,
                        height: 61,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
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
                      item.title,
                      style: AppTypography.bodyEmphasized.copyWith(color: AppColors.black),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (item.dateLabel != null && item.dateLabel!.trim().isNotEmpty) ...[
                    const SizedBox(height: _contentGap),
                    DsNewsReadingTime(label: item.dateLabel!.trim()),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Module : titre + **PageView** aligné sur [MarketingCardsSlidingModule] (`viewportFraction: 1`,
/// `padEnds: false`, mêmes paddings : bords [kModuleHorizontalMargin], entre cartes [AppSpacing.md]
/// en demi‑gouttières). Bullets via [onPageChanged]. Comportement de slide **cranté** (physique page).
class VideoBlockArticleModule extends StatefulWidget {
  const VideoBlockArticleModule({
    super.key,
    this.title = 'Vidéos',
    required this.items,
    this.onTitleTap,
  });

  final String title;
  final List<VideoBlockArticleItemData> items;
  final VoidCallback? onTitleTap;

  @override
  State<VideoBlockArticleModule> createState() => _VideoBlockArticleModuleState();
}

class _VideoBlockArticleModuleState extends State<VideoBlockArticleModule> {
  double? _measuredHeight;
  bool _measureScheduled = false;
  final GlobalKey _measureKey = GlobalKey();
  late PageController _pageController;
  int _currentPage = 0;

  /// Comme [MarketingCardsSlidingModule].
  static const double _gapBetweenCards = AppSpacing.md;
  static const double _shadowPaddingVertical = AppSpacing.sm;
  static const double _titleToCarouselGap = AppSpacing.md - _shadowPaddingVertical;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(viewportFraction: 1);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _measureCardHeight() {
    final box = _measureKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize || !mounted) return;
    setState(() => _measuredHeight = box.size.height);
  }

  static const double _minCardHeight =
      VideoBlockArticle._imageSectionHeight + 8 + 66 + 8 + 18 + 16;

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    /// Largeur « page milieu » = même logique que [MarketingCardsSlidingModule] (mesure hauteur).
    final measureCardW = math.max(0.0, screenWidth - _gapBetweenCards);

    if (_measuredHeight == null && !_measureScheduled) {
      _measureScheduled = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _measureCardHeight());
    }

    final height = _measuredHeight;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: kModuleHorizontalMargin),
          child: widget.onTitleTap != null
              ? Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: widget.onTitleTap,
                    borderRadius: BorderRadius.circular(4),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            widget.title,
                            style: AppTypography.sectionTitle.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.xs),
                          Icon(
                            Icons.chevron_right,
                            size: 22,
                            color: AppColors.textPrimary,
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              : Text(
                  widget.title,
                  style: AppTypography.sectionTitle.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
        ),
        SizedBox(height: _titleToCarouselGap),
        if (height != null && height > 0)
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                height:
                    math.max(height, _minCardHeight) + _shadowPaddingVertical,
                child: Padding(
                  padding: const EdgeInsets.only(top: _shadowPaddingVertical),
                  child: PageView.builder(
                    controller: _pageController,
                    onPageChanged: (index) =>
                        setState(() => _currentPage = index),
                    itemCount: widget.items.length,
                    padEnds: false,
                    itemBuilder: (context, index) {
                      final last = widget.items.length - 1;
                      final left = index == 0
                          ? kModuleHorizontalMargin
                          : _gapBetweenCards / 2;
                      final right = index == last
                          ? kModuleHorizontalMargin
                          : _gapBetweenCards / 2;
                      return Padding(
                        padding: EdgeInsets.only(left: left, right: right),
                        child: VideoBlockArticle(
                          item: widget.items[index],
                          onTap: widget.items[index].onTap,
                        ),
                      );
                    },
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              CarouselPaginationDots(
                count: widget.items.length,
                activeIndex: _currentPage,
              ),
            ],
          )
        else
          Offstage(
            child: SizedBox(
              key: _measureKey,
              width: measureCardW,
              child: VideoBlockArticle(
                item: widget.items.first,
                onTap: widget.items.first.onTap,
              ),
            ),
          ),
      ],
    );
  }
}
