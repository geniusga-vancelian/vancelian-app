import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../atoms/app_colors.dart';

/// Checkbox with optional rich description supporting markdown-style links.
///
/// The ENTIRE widget area toggles the checkbox on tap.
/// Links inside the description open URLs instead of toggling.
///
/// Uses a single [GestureDetector] covering the full widget area.
/// Link detection is done via [TextPainter] position math — no TextSpan
/// recognizers — which avoids all gesture-arena conflicts.
class AppCheckbox extends StatefulWidget {
  const AppCheckbox({
    super.key,
    this.checked = false,
    this.disabled = false,
    this.label,
    this.description,
    this.onChanged,
  });

  final bool checked;
  final bool disabled;
  final String? label;
  final String? description;
  final ValueChanged<bool>? onChanged;

  @override
  State<AppCheckbox> createState() => _AppCheckboxState();
}

class _AppCheckboxState extends State<AppCheckbox> {
  static const _size = 24.0;
  static const _radius = 6.0;
  static const _borderDefault = Color(0xFFD1D1D6);
  static const _borderDisabled = Color(0xFFC7C7CC);
  static const _fillDisabled = Color(0xFFEFEEFE);
  static const _labelColor = Color(0xFF2C2C2E);
  static const _descColor = Color(0xFF636366);

  static final _linkRe = RegExp(r'\[([^\]]+)\]\(([^)]+)\)');

  final _descKey = GlobalKey();

  late _ParsedDesc? _parsed = _parseDesc();

  @override
  void didUpdateWidget(covariant AppCheckbox old) {
    super.didUpdateWidget(old);
    if (old.description != widget.description) {
      _parsed = _parseDesc();
    }
  }

  _ParsedDesc? _parseDesc() {
    final raw = widget.description;
    if (raw == null || raw.isEmpty) return null;

    final spans = <InlineSpan>[];
    final links = <_LinkRange>[];
    var lastEnd = 0;
    var charOffset = 0;

    for (final m in _linkRe.allMatches(raw)) {
      if (m.start > lastEnd) {
        final plain = raw.substring(lastEnd, m.start);
        spans.add(TextSpan(text: plain));
        charOffset += plain.length;
      }
      final linkText = m.group(1)!;
      final url = m.group(2)!;
      links.add(_LinkRange(charOffset, charOffset + linkText.length, url));
      spans.add(TextSpan(
        text: linkText,
        style: const TextStyle(
          color: AppColors.indigo,
          fontWeight: FontWeight.w500,
          decoration: TextDecoration.none,
        ),
      ));
      charOffset += linkText.length;
      lastEnd = m.end;
    }

    if (lastEnd < raw.length) {
      spans.add(TextSpan(text: raw.substring(lastEnd)));
    }

    final rootSpan = TextSpan(
      style: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 20 / 14,
        letterSpacing: -0.15,
        color: _descColor,
      ),
      children: spans,
    );

    return _ParsedDesc(rootSpan, links);
  }

  void _handleTapUp(TapUpDetails details) {
    if (widget.disabled) return;

    if (_parsed != null && _parsed!.links.isNotEmpty) {
      final ro = _descKey.currentContext?.findRenderObject();
      if (ro is RenderBox && ro.hasSize) {
        final local = ro.globalToLocal(details.globalPosition);
        if (local.dx >= 0 &&
            local.dy >= 0 &&
            local.dx <= ro.size.width &&
            local.dy <= ro.size.height) {
          final tp = TextPainter(
            text: _parsed!.span,
            textDirection: TextDirection.ltr,
            textScaler: MediaQuery.textScalerOf(context),
          )..layout(maxWidth: ro.size.width);

          final pos = tp.getPositionForOffset(local);
          tp.dispose();

          for (final link in _parsed!.links) {
            if (pos.offset >= link.start && pos.offset < link.end) {
              _openUrl(link.url);
              return;
            }
          }
        }
      }
    }

    final onChanged = widget.onChanged;
    if (onChanged != null) {
      onChanged(!widget.checked);
      // Même retour haptique que [FormCheckboxRow] / [SelectableMultiList].
      Future.microtask(HapticFeedback.selectionClick);
    }
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Widget _buildBox() {
    if (widget.disabled && !widget.checked) {
      return Container(
        width: _size,
        height: _size,
        decoration: BoxDecoration(
          color: _fillDisabled,
          borderRadius: BorderRadius.circular(_radius),
          border: Border.all(color: _borderDisabled),
        ),
      );
    }

    if (widget.disabled && widget.checked) {
      return SizedBox(
        width: _size,
        height: _size,
        child: Stack(
          children: [
            Container(
              width: _size,
              height: _size,
              decoration: BoxDecoration(
                color: AppColors.indigo,
                borderRadius: BorderRadius.circular(_radius),
              ),
              child: const Center(child: _CheckIcon()),
            ),
            Container(
              width: _size,
              height: _size,
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(_radius),
              ),
            ),
          ],
        ),
      );
    }

    if (widget.checked) {
      return Container(
        width: _size,
        height: _size,
        decoration: BoxDecoration(
          color: AppColors.indigo,
          borderRadius: BorderRadius.circular(_radius),
        ),
        child: const Center(child: _CheckIcon()),
      );
    }

    return Container(
      width: _size,
      height: _size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(_radius),
        border: Border.all(color: _borderDefault),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasLabel =
        widget.label != null && widget.label!.isNotEmpty;
    final hasDesc = _parsed != null;

    return GestureDetector(
      onTapUp: _handleTapUp,
      behavior: HitTestBehavior.opaque,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 1),
            child: _buildBox(),
          ),
          const SizedBox(width: 12),
          if (hasLabel || hasDesc)
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (hasLabel)
                    Text(
                      widget.label!,
                      style: GoogleFonts.inter(
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                        height: 22 / 15,
                        letterSpacing: -0.23,
                        color: _labelColor,
                      ),
                    ),
                  if (hasDesc) ...[
                    if (hasLabel) const SizedBox(height: 4),
                    Text.rich(_parsed!.span, key: _descKey),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ParsedDesc {
  const _ParsedDesc(this.span, this.links);
  final TextSpan span;
  final List<_LinkRange> links;
}

class _LinkRange {
  const _LinkRange(this.start, this.end, this.url);
  final int start;
  final int end;
  final String url;
}

class _CheckIcon extends StatelessWidget {
  const _CheckIcon();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(14, 14),
      painter: _CheckPainter(),
    );
  }
}

class _CheckPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;

    final path = Path()
      ..moveTo(size.width * 0.18, size.height * 0.5)
      ..lineTo(size.width * 0.42, size.height * 0.73)
      ..lineTo(size.width * 0.82, size.height * 0.28);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
