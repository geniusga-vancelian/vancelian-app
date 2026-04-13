import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Bloc citation pour un article (news, aide, etc.).
///
/// - **Card** ([asCard] = true) : carte blanche arrondie, **barre d’accent** indigo à gauche
///   qui épouse les coins (comme Figma), guillemets, citation en [AppTypography.bodyItalic],
///   auteur en [AppTypography.bodySmItalic] gris **aligné à droite** sous la citation.
/// - **Inline** ([asCard] = false) : bordure gauche indigo, texte italique (variante compacte).
class ArticleQuoteBlock extends StatelessWidget {
  final String quote;
  final String? author;
  final bool asCard;

  const ArticleQuoteBlock({
    super.key,
    required this.quote,
    this.author,
    this.asCard = true,
  });

  @override
  Widget build(BuildContext context) {
    if (asCard) return _buildCard();
    return _buildInline();
  }

  Widget _buildInline() {
    final authorTrimmed = author?.trim();
    return Container(
      decoration: const BoxDecoration(
        border: Border(
          left: BorderSide(color: AppColors.accent, width: 2),
        ),
      ),
      padding: const EdgeInsets.only(left: AppSpacing.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            quote.trim(),
            style: AppTypography.bodyItalic.copyWith(
              color: AppColors.black,
            ),
          ),
          if (authorTrimmed != null && authorTrimmed.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.s2),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                authorTrimmed,
                textAlign: TextAlign.right,
                style: AppTypography.bodySmItalic.copyWith(
                  color: AppColors.gray,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  static const double _cardRadius = AppRadius.lg;
  static const double _accentBarWidth = 4;

  Widget _buildCard() {
    final authorTrimmed = author?.trim();
    final q = quote.trim();
    if (q.isEmpty) return const SizedBox.shrink();

    return ClipRRect(
      borderRadius: BorderRadius.circular(_cardRadius),
      child: ColoredBox(
        color: AppColors.white,
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                width: _accentBarWidth,
                decoration: const BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(_cardRadius),
                    bottomLeft: Radius.circular(_cardRadius),
                  ),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.s4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const _QuoteIcon(color: AppColors.accent),
                      const SizedBox(height: AppSpacing.s2),
                      Text(
                        q,
                        style: AppTypography.bodyItalic.copyWith(
                          color: AppColors.black,
                        ),
                      ),
                      if (authorTrimmed != null && authorTrimmed.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.s3),
                        Align(
                          alignment: Alignment.centerRight,
                          child: Text(
                            authorTrimmed,
                            textAlign: TextAlign.right,
                            style: AppTypography.bodySmItalic.copyWith(
                              color: AppColors.gray,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuoteIcon extends StatelessWidget {
  const _QuoteIcon({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 20,
      height: 14,
      child: CustomPaint(painter: _QuoteIconPainter(color: color)),
    );
  }
}

class _QuoteIconPainter extends CustomPainter {
  _QuoteIconPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;

    final path1 = Path()
      ..moveTo(1.204 * size.width / 20, 6.531 * size.height / 14)
      ..lineTo(3.871 * size.width / 20, 6.531 * size.height / 14)
      ..cubicTo(
        3.871 * size.width / 20, 6.531 * size.height / 14,
        3.660 * size.width / 20, 10.292 * size.height / 14,
        0, 12.053 * size.height / 14,
      )
      ..lineTo(0.829 * size.width / 20, size.height)
      ..cubicTo(
        0.829 * size.width / 20, size.height,
        1.076 * size.width / 20, 13.975 * size.height / 14,
        1.489 * size.width / 20, 13.891 * size.height / 14,
      )
      ..cubicTo(
        6.092 * size.width / 20, 12.946 * size.height / 14,
        9.375 * size.width / 20, 9.012 * size.height / 14,
        9.375 * size.width / 20, 4.472 * size.height / 14,
      )
      ..lineTo(9.375 * size.width / 20, 0)
      ..lineTo(1.204 * size.width / 20, 0)
      ..close();

    final path2 = Path()
      ..moveTo(11.828 * size.width / 20, 0)
      ..lineTo(11.828 * size.width / 20, 6.531 * size.height / 14)
      ..lineTo(14.495 * size.width / 20, 6.531 * size.height / 14)
      ..cubicTo(
        14.495 * size.width / 20, 6.531 * size.height / 14,
        14.284 * size.width / 20, 10.292 * size.height / 14,
        10.625 * size.width / 20, 12.053 * size.height / 14,
      )
      ..lineTo(11.454 * size.width / 20, size.height)
      ..cubicTo(
        11.454 * size.width / 20, size.height,
        11.701 * size.width / 20, 13.975 * size.height / 14,
        12.113 * size.width / 20, 13.891 * size.height / 14,
      )
      ..cubicTo(
        16.716 * size.width / 20, 12.946 * size.height / 14,
        size.width, 9.012 * size.height / 14,
        size.width, 4.472 * size.height / 14,
      )
      ..lineTo(size.width, 0)
      ..close();

    canvas.drawPath(path1, paint);
    canvas.drawPath(path2, paint);
  }

  @override
  bool shouldRepaint(covariant _QuoteIconPainter oldDelegate) =>
      oldDelegate.color != color;
}
