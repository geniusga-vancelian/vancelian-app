import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// State of the text input field.
enum AppTextInputState { idle, focused, error }

/// Label behaviour variant.
///
/// [floatingLabel] – the label shrinks and floats above the value (default).
/// [placeholder]  – the label stays centred as a hint and fades out once text
///                   is entered.
enum AppTextInputVariant { floatingLabel, placeholder }

/// Generic text input with animated floating label that stays **inside** the
/// container (not straddling the border). Matches the Figma "filled input"
/// spec with a white rounded background.
///
/// Figma spec:
///   - Background: white, border-radius: 16px, padding: 16px
///   - Label: Inter SemiBold 17px → 11px when floating, color #8E8E93
///   - Focused border: 1px solid #6155F5
///   - Error border: 1px solid #FF2D55
///   - Description: Inter Regular 13px, color #808080
///   - Error text: Inter Regular 13px, color #FF2D55
class AppTextInput extends StatefulWidget {
  const AppTextInput({
    super.key,
    this.label = 'Label',
    this.variant = AppTextInputVariant.floatingLabel,
    this.controller,
    this.focusNode,
    this.onChanged,
    this.description,
    this.error,
    this.obscureText = false,
    this.showEmailIcon = false,
    this.showClearButton = false,
    this.showPasswordToggle = false,
    this.keyboardType,
    this.textInputAction,
    this.autofocus = false,
  });

  final String label;
  final AppTextInputVariant variant;
  final TextEditingController? controller;
  final FocusNode? focusNode;
  final ValueChanged<String>? onChanged;
  final String? description;
  final String? error;
  final bool obscureText;
  final bool showEmailIcon;
  final bool showClearButton;
  final bool showPasswordToggle;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool autofocus;

  @override
  State<AppTextInput> createState() => _AppTextInputState();
}

class _AppTextInputState extends State<AppTextInput> {
  late TextEditingController _ctrl;
  FocusNode? _internalFocusNode;
  bool _hasFocus = false;
  bool _obscured = true;

  static const _radius = 16.0;
  static const _containerHeight = 56.0;
  static const _labelColor = Color(0xFF8E8E93);

  static const _descColor = Color(0xFF808080);
  static const _errorColor = Color(0xFFFF2D55);

  FocusNode get _focusNode => widget.focusNode ?? (_internalFocusNode ??= FocusNode());

  @override
  void initState() {
    super.initState();
    _ctrl = widget.controller ?? TextEditingController();
    _focusNode.addListener(_onFocusChange);
    _obscured = widget.obscureText;
  }

  @override
  void didUpdateWidget(covariant AppTextInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.focusNode != widget.focusNode) {
      (oldWidget.focusNode ?? _internalFocusNode)?.removeListener(_onFocusChange);
      _focusNode.addListener(_onFocusChange);
      _hasFocus = _focusNode.hasFocus;
    }
  }

  @override
  void dispose() {
    if (widget.controller == null) _ctrl.dispose();
    _focusNode.removeListener(_onFocusChange);
    _internalFocusNode?.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    if (_focusNode.hasFocus != _hasFocus) {
      setState(() => _hasFocus = _focusNode.hasFocus);
    }
  }

  bool get _hasError => widget.error != null && widget.error!.isNotEmpty;
  bool get _isFloating => _hasFocus || _ctrl.text.isNotEmpty;
  bool get _isPlaceholderMode =>
      widget.variant == AppTextInputVariant.placeholder;

  Color get _borderColor {
    if (_hasError) return _errorColor;
    if (_hasFocus) return AppColors.indigo;
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeInOut,
          height: _containerHeight,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(_radius),
            border: Border.all(color: _borderColor, width: 1.5),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              if (widget.showEmailIcon)
                const Padding(
                  padding: EdgeInsets.only(right: 8),
                  child: Icon(Icons.email_outlined,
                      size: 24, color: _labelColor),
                ),
              Expanded(
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: Theme(
                        data: Theme.of(context).copyWith(
                          textSelectionTheme: TextSelectionThemeData(
                            selectionColor:
                                AppColors.indigo.withValues(alpha: 0.15),
                            cursorColor: AppColors.indigo,
                            selectionHandleColor: AppColors.indigo,
                          ),
                        ),
                          child: TextField(
                          controller: _ctrl,
                          focusNode: _focusNode,
                          autofocus: widget.autofocus,
                          cursorColor: AppColors.indigo,
                          textInputAction: widget.textInputAction,
                          onChanged: (v) {
                            widget.onChanged?.call(v);
                            setState(() {});
                          },
                          obscureText: widget.showPasswordToggle
                              ? _obscured
                              : widget.obscureText,
                          keyboardType: widget.keyboardType,
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
                            isDense: true,
                            filled: false,
                            contentPadding: _isPlaceholderMode
                                ? EdgeInsets.zero
                                : const EdgeInsets.only(top: 24, bottom: 4),
                            hintText: _isPlaceholderMode ? widget.label : null,
                            hintStyle: _isPlaceholderMode
                                ? GoogleFonts.inter(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    height: 22 / 17,
                                    letterSpacing: -0.43,
                                    color: _labelColor,
                                  )
                                : null,
                          ),
                          expands: _isPlaceholderMode,
                          maxLines: _isPlaceholderMode ? null : 1,
                          textAlignVertical: _isPlaceholderMode
                              ? TextAlignVertical.center
                              : TextAlignVertical.top,
                        ),
                      ),
                    ),
                    if (!_isPlaceholderMode)
                      // Floating label: shrinks and moves up on focus/text
                      AnimatedPositioned(
                        duration: const Duration(milliseconds: 150),
                        curve: Curves.easeInOut,
                        top: _isFloating ? 8 : 16,
                        left: 0,
                        child: IgnorePointer(
                          child: AnimatedDefaultTextStyle(
                            duration: const Duration(milliseconds: 150),
                            curve: Curves.easeInOut,
                            style: _isFloating
                                ? GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    height: 13 / 11,
                                    letterSpacing: 0.06,
                                    color: _hasError
                                        ? _errorColor
                                        : const Color(0xFFD1D1D6),
                                  )
                                : GoogleFonts.inter(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    height: 22 / 17,
                                    letterSpacing: -0.43,
                                    color: _labelColor,
                                  ),
                            child: Text(widget.label),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              ..._buildSuffixIcons(),
            ],
          ),
        ),
        if (widget.description != null && !_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              widget.description!,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                height: 16 / 13,
                letterSpacing: -0.08,
                color: _descColor,
              ),
            ),
          ),
        if (_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              widget.error!,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                height: 16 / 13,
                letterSpacing: -0.08,
                color: _errorColor,
              ),
            ),
          ),
      ],
    );
  }

  List<Widget> _buildSuffixIcons() {
    final icons = <Widget>[];
    if (widget.showClearButton && _ctrl.text.isNotEmpty) {
      icons.add(Padding(
        padding: const EdgeInsets.only(left: 8),
        child: GestureDetector(
          onTap: () {
            _ctrl.clear();
            widget.onChanged?.call('');
            setState(() {});
          },
          child: Container(
            width: 24,
            height: 24,
            decoration: const BoxDecoration(
              color: Color(0xFFE5E5EA),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.close_rounded,
                size: 16, color: Colors.white),
          ),
        ),
      ));
    }
    if (widget.showPasswordToggle) {
      icons.add(Padding(
        padding: const EdgeInsets.only(left: 8),
        child: GestureDetector(
          onTap: () => setState(() => _obscured = !_obscured),
          child: Icon(
            _obscured
                ? Icons.visibility_outlined
                : Icons.visibility_off_outlined,
            size: 24,
            color: _labelColor,
          ),
        ),
      ));
    }
    return icons;
  }
}
