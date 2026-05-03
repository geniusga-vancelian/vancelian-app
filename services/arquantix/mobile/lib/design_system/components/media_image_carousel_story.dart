import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/kalai_icons.dart';
import 'ds_story_segment_bar.dart';
import 'kalai_icon.dart';
import 'wave_dots_loading_indicator.dart';

/// Item du carousel : URL d'image + texte alternatif optionnel.
class MediaImageCarouselItem {
  const MediaImageCarouselItem({required this.url, this.alt});

  final String url;
  final String? alt;
}

/// Carousel d'images type « stories Instagram » :
/// - Image plein cadre, ratio configurable, coins arrondis.
/// - [DsStorySegmentBar] (variant `onMedia`) en overlay haut.
/// - **Tap** sur l'image : avance d'une image (sens unique, comme Instagram —
///   peut boucler si [loop] est `true`).
/// - **Swipe** horizontal au doigt (PageView natif) : navigation bidirectionnelle.
/// - Loader [WaveDotsLoadingIndicator] centré pendant le chargement de chaque
///   image (utilise `Image.network` + `loadingBuilder`).
/// - Placeholder (fond [placeholderColor]) tant que l'image n'est pas dispo
///   ou en cas d'erreur réseau.
class MediaImageCarouselStory extends StatefulWidget {
  const MediaImageCarouselStory({
    required this.items,
    super.key,
    this.aspectRatio = 16 / 9,
    this.borderRadius = AppRadius.lg,
    this.loop = false,
    this.placeholderColor = const Color(0xFFC9D1E5),
  });

  final List<MediaImageCarouselItem> items;

  /// Ratio largeur / hauteur (ex. 16/9 ≈ 1.78). Le widget se cale sur la
  /// largeur disponible et calcule la hauteur via ce ratio.
  final double aspectRatio;

  /// Rayon des coins (clip image + ombre). Défaut [AppRadius.lg] (16 px).
  final double borderRadius;

  /// Si `true`, le tap après la dernière image revient à la première.
  final bool loop;

  /// Couleur de fond avant chargement / si l'image échoue (≈ Figma bleu pâle).
  final Color placeholderColor;

  @override
  State<MediaImageCarouselStory> createState() => _MediaImageCarouselStoryState();
}

class _MediaImageCarouselStoryState extends State<MediaImageCarouselStory> {
  late final PageController _controller;
  int _index = 0;

  @override
  void initState() {
    super.initState();
    _controller = PageController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _goToNext() {
    final count = widget.items.length;
    if (count <= 1) return;
    final isLast = _index >= count - 1;
    if (isLast && !widget.loop) return;
    final next = isLast ? 0 : _index + 1;
    _controller.animateToPage(
      next,
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = widget.items;
    if (items.isEmpty) return const SizedBox.shrink();

    return AspectRatio(
      aspectRatio: widget.aspectRatio,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(widget.borderRadius),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Container(color: widget.placeholderColor),
            PageView.builder(
              controller: _controller,
              itemCount: items.length,
              onPageChanged: (i) => setState(() => _index = i),
              itemBuilder: (context, i) => _CarouselSlide(
                item: items[i],
                placeholderColor: widget.placeholderColor,
              ),
            ),
            // Tap forward (zone plein cadre, sens unique).
            // Posé après PageView pour intercepter le tap mais en `behavior:
            // HitTestBehavior.translucent` les drags continuent d'être captés
            // par le PageView en dessous (drag absorbe les pointeurs avant tap).
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: _goToNext,
              ),
            ),
            if (items.length > 1)
              Positioned(
                top: 12,
                left: 8,
                right: 8,
                child: DsStorySegmentBar(
                  segmentCount: items.length,
                  activeIndex: _index,
                  variant: DsStorySegmentBarVariant.onMedia,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _CarouselSlide extends StatelessWidget {
  const _CarouselSlide({required this.item, required this.placeholderColor});

  final MediaImageCarouselItem item;
  final Color placeholderColor;

  @override
  Widget build(BuildContext context) {
    /// Stack `expand` + image en `width/height: infinity` + `BoxFit.cover` :
    /// l'image remplit **100 %** du module, ratio préservé (zoom in/out auto,
    /// pas d'étirement).
    return Stack(
      fit: StackFit.expand,
      children: [
        ColoredBox(color: placeholderColor),
        Image.network(
          item.url,
          width: double.infinity,
          height: double.infinity,
          fit: BoxFit.cover,
          semanticLabel: item.alt,
          gaplessPlayback: true,
          frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
            if (wasSynchronouslyLoaded) return child;
            return AnimatedOpacity(
              opacity: frame == null ? 0 : 1,
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOut,
              child: child,
            );
          },
          loadingBuilder: (context, child, progress) {
            // `progress == null` → image décodée et prête : on retourne le
            // child tel quel (l'AnimatedOpacity du frameBuilder gère le fade-in).
            if (progress == null) return child;
            return Stack(
              fit: StackFit.expand,
              children: [
                child,
                const Center(
                  child: WaveDotsLoadingIndicator(
                    color: AppColors.white,
                    dotSize: 7,
                    spacing: 8,
                  ),
                ),
              ],
            );
          },
          errorBuilder: (context, error, stack) => const Center(
            child: KalaiIcon(
              KalaiIcons.photoOff,
              color: AppColors.white,
              size: 32,
            ),
          ),
        ),
      ],
    );
  }
}
