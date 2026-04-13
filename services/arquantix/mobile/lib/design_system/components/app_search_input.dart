import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Visual variant for [AppSearchInput].
enum AppSearchInputVariant { white, gray, focused }

/// Search input field with magnifying glass icon and clear button.
///
/// Figma spec:
///   - Height: 55px, border-radius: 16px
///   - Padding: 16px horizontal, 8px vertical
///   - Gap: 8px between icon and text
///   - Placeholder: Inter SemiBold 17px, tracking -0.43px, color #8E8E93
///   - Label (focused): Inter SemiBold 11px/13px, tracking 0.06px, color #B3B3B3
///   - Focused border: 1px solid #6155F5 (AppColors.indigo)
class AppSearchInput extends StatefulWidget {
  const AppSearchInput({
    super.key,
    this.placeholder = 'Rechercher',
    this.controller,
    this.onChanged,
    this.onSubmitted,
    this.variant = AppSearchInputVariant.white,
    this.autofocus = false,
    this.isLoading = false,
    this.textFieldKey,
  });

  final String placeholder;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final AppSearchInputVariant variant;
  final bool autofocus;

  /// Affiche un indicateur à la place du bouton effacer (ex. autocomplete réseau).
  final bool isLoading;

  /// Clé sur le [TextField] interne (tests, sémantique).
  final Key? textFieldKey;

  @override
  State<AppSearchInput> createState() => _AppSearchInputState();
}

class _AppSearchInputState extends State<AppSearchInput> {
  late TextEditingController _ctrl;
  late FocusNode _focusNode;
  bool _hasFocus = false;

  static const _height = 55.0;
  static const _radius = 16.0;
  static const _iconColor = Color(0xFF8E8E93);
  static const _clearBg = Color(0xFFE5E5EA);

  @override
  void initState() {
    super.initState();
    _ctrl = widget.controller ?? TextEditingController();
    _focusNode = FocusNode()..addListener(_onFocusChange);
  }

  @override
  void dispose() {
    if (widget.controller == null) _ctrl.dispose();
    _focusNode.removeListener(_onFocusChange);
    _focusNode.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    if (_focusNode.hasFocus != _hasFocus) {
      setState(() => _hasFocus = _focusNode.hasFocus);
    }
  }

  bool get _showBorder =>
      widget.variant == AppSearchInputVariant.focused || _hasFocus;

  Color get _bgColor {
    switch (widget.variant) {
      case AppSearchInputVariant.gray:
        return AppColors.pageBackground;
      case AppSearchInputVariant.white:
      case AppSearchInputVariant.focused:
        return Colors.white;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      height: _height,
      decoration: BoxDecoration(
        color: _bgColor,
        borderRadius: BorderRadius.circular(_radius),
        border: _showBorder
            ? Border.all(color: AppColors.indigo, width: 1.5)
            : Border.all(color: Colors.transparent, width: 1.5),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          const Icon(Icons.search_rounded, size: 24, color: _iconColor),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              key: widget.textFieldKey,
              controller: _ctrl,
              focusNode: _focusNode,
              autofocus: widget.autofocus,
              textInputAction: TextInputAction.search,
              onChanged: (v) {
                widget.onChanged?.call(v);
                setState(() {});
              },
              onSubmitted: widget.onSubmitted,
              style: GoogleFonts.inter(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                height: 1.0,
                letterSpacing: -0.43,
                color: Colors.black,
              ),
              decoration: InputDecoration(
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                isCollapsed: true,
                filled: false,
                contentPadding: EdgeInsets.zero,
                hintText: widget.placeholder,
                hintStyle: GoogleFonts.inter(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  height: 22 / 17,
                  letterSpacing: -0.43,
                  color: _iconColor,
                ),
              ),
            ),
          ),
          if (widget.isLoading)
            const Padding(
              padding: EdgeInsets.all(4),
              child: SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.indigo,
                ),
              ),
            )
          else if (_ctrl.text.isNotEmpty)
            GestureDetector(
              onTap: () {
                _ctrl.clear();
                widget.onChanged?.call('');
                setState(() {});
              },
              child: Container(
                width: 24,
                height: 24,
                decoration: const BoxDecoration(
                  color: _clearBg,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.close_rounded, size: 16, color: Colors.white),
              ),
            ),
        ],
      ),
    );
  }
}
